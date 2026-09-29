"""Log e cota das chamadas Sienge feitas por este ERP.

Pacote Ultimate (aditivo 8, 2022). A cota diária do Sienge ignora HTTP 401 e 5xx.
HTTP 429 conta (estouro). Falha ao gravar o log não pode subir até o sync.
"""

from __future__ import annotations

import calendar
import logging
import urllib.parse
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, inspect
from sqlalchemy.orm import Session

from app.models.sienge_api_call import SiengeApiCall

logger = logging.getLogger(__name__)

# Tetos do pacote Ultimate (aditivo 8, 2022).
REST_DAILY_LIMIT = 75_000
BULK_DAILY_LIMIT = 28_800
REST_PER_MINUTE_LIMIT = 200
BULK_PER_MINUTE_LIMIT = 20

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
PACKAGE_NAME = "Ultimate"

_LIMITS = {
    "REST": (REST_DAILY_LIMIT, REST_PER_MINUTE_LIMIT),
    "BULK": (BULK_DAILY_LIMIT, BULK_PER_MINUTE_LIMIT),
}


def classify_sienge_family(url: str) -> str:
    path = urllib.parse.urlsplit(url or "").path.lower()
    if "/bulk-data/" in path or path.rstrip("/").endswith("/bulk-data"):
        return "BULK"
    return "REST"


def safe_request_path(url: str) -> str:
    """Caminho sem query, fragmento, usuário ou senha."""
    path = urllib.parse.urlsplit(url or "").path or "/"
    return path[:512]


def counts_toward_quota(status_code: int | None) -> bool:
    if status_code is None:
        return False
    if status_code == 401 or status_code >= 500:
        return False
    return True


def _quota_expr():
    return case(
        (
            and_(
                SiengeApiCall.status_code.isnot(None),
                SiengeApiCall.status_code != 401,
                SiengeApiCall.status_code < 500,
            ),
            1,
        ),
        else_=0,
    )


def month_utc_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start_local = datetime(year, month, 1, tzinfo=SAO_PAULO)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=SAO_PAULO)
    else:
        end_local = datetime(year, month + 1, 1, tzinfo=SAO_PAULO)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def elapsed_days_in_month(year: int, month: int, today: date) -> int:
    start = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    if today < start:
        return 0
    end = min(today, last)
    return (end - start).days + 1


def _utc_naive_to_sp_date(value: datetime) -> date:
    aware = value.replace(tzinfo=timezone.utc)
    return aware.astimezone(SAO_PAULO).date()


def _day_expr(dialect: str):
    column = SiengeApiCall.created_at
    if dialect == "postgresql":
        local_ts = func.timezone("America/Sao_Paulo", func.timezone("UTC", column))
        return func.date(local_ts)
    return func.date(column, "-3 hours")


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def record_sienge_http_call(
    *,
    url: str,
    method: str,
    status_code: int | None,
    duration_ms: int,
) -> None:
    """Grava uma chamada. Qualquer erro é engolido."""
    try:
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            db.add(
                SiengeApiCall(
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    family=classify_sienge_family(url),
                    method=(method or "GET")[:8],
                    path=safe_request_path(url),
                    status_code=int(status_code) if status_code is not None else None,
                    duration_ms=max(0, int(duration_ms)),
                )
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning("Falha ao gravar log de consumo da API Sienge")
        finally:
            db.close()
    except Exception:
        logger.warning("Falha ao gravar log de consumo da API Sienge")


def _empty_family(family: str, year: int, month: int) -> dict:
    daily, per_minute = _LIMITS[family]
    last = calendar.monthrange(year, month)[1]
    days = [
        {
            "data": date(year, month, day).isoformat(),
            "total": None,
            "medido": False,
            "acima_do_limite": False,
        }
        for day in range(1, last + 1)
    ]
    return {
        "familia": family,
        "limite_diario": daily,
        "limite_por_minuto": per_minute,
        "total": None,
        "media_diaria": None,
        "maior_dia": None,
        "maior_dia_total": None,
        "http_429": 0,
        "http_401": 0,
        "http_5xx": 0,
        "dias": days,
    }


def empty_month_report(year: int, month: int) -> dict:
    return {
        "ano": year,
        "mes": month,
        "fuso": "America/Sao_Paulo",
        "pacote": PACKAGE_NAME,
        "historico_vazio": True,
        "familias": [_empty_family("REST", year, month), _empty_family("BULK", year, month)],
        "endpoints": [],
    }


def build_month_report(db: Session, year: int, month: int, *, today: date | None = None) -> dict:
    bind = db.get_bind()
    if not inspect(bind).has_table(SiengeApiCall.__tablename__):
        return empty_month_report(year, month)

    first_at = db.query(func.min(SiengeApiCall.created_at)).scalar()
    if first_at is None:
        return empty_month_report(year, month)

    first_day = _utc_naive_to_sp_date(first_at)
    today = today or datetime.now(SAO_PAULO).date()
    start_utc, end_utc = month_utc_bounds(year, month)
    quota = _quota_expr()
    day_col = _day_expr(bind.dialect.name).label("dia")
    is_429 = case((SiengeApiCall.status_code == 429, 1), else_=0)
    is_401 = case((SiengeApiCall.status_code == 401, 1), else_=0)
    is_5xx = case((SiengeApiCall.status_code >= 500, 1), else_=0)

    rows = (
        db.query(
            day_col,
            SiengeApiCall.family,
            func.sum(quota).label("total"),
            func.sum(is_429).label("http_429"),
            func.sum(is_401).label("http_401"),
            func.sum(is_5xx).label("http_5xx"),
        )
        .filter(SiengeApiCall.created_at >= start_utc, SiengeApiCall.created_at < end_utc)
        .group_by(day_col, SiengeApiCall.family)
        .all()
    )

    by_family: dict[str, dict[date, dict]] = {"REST": {}, "BULK": {}}
    extras = {
        "REST": {"http_429": 0, "http_401": 0, "http_5xx": 0},
        "BULK": {"http_429": 0, "http_401": 0, "http_5xx": 0},
    }
    for row in rows:
        family = row.family if row.family in by_family else "REST"
        day = _as_date(row.dia)
        by_family[family][day] = {"total": int(row.total or 0)}
        extras[family]["http_429"] += int(row.http_429 or 0)
        extras[family]["http_401"] += int(row.http_401 or 0)
        extras[family]["http_5xx"] += int(row.http_5xx or 0)

    elapsed = elapsed_days_in_month(year, month, today)
    last = calendar.monthrange(year, month)[1]
    families = []
    for family in ("REST", "BULK"):
        daily_limit, per_minute = _LIMITS[family]
        days = []
        month_total = 0
        peak_day = None
        peak_total = -1
        for day_num in range(1, last + 1):
            day = date(year, month, day_num)
            measured = day >= first_day and day <= today
            total = by_family[family].get(day, {}).get("total", 0) if measured else None
            if measured:
                month_total += total or 0
                if (total or 0) > peak_total:
                    peak_total = total or 0
                    peak_day = day.isoformat()
            days.append(
                {
                    "data": day.isoformat(),
                    "total": total,
                    "medido": measured,
                    "acima_do_limite": bool(measured and (total or 0) > daily_limit),
                }
            )
        families.append(
            {
                "familia": family,
                "limite_diario": daily_limit,
                "limite_por_minuto": per_minute,
                "total": month_total,
                "media_diaria": round(month_total / elapsed, 1) if elapsed else None,
                "maior_dia": peak_day if peak_total > 0 else None,
                "maior_dia_total": peak_total if peak_total > 0 else None,
                "http_429": extras[family]["http_429"],
                "http_401": extras[family]["http_401"],
                "http_5xx": extras[family]["http_5xx"],
                "dias": days,
            }
        )

    endpoint_rows = (
        db.query(
            SiengeApiCall.path,
            SiengeApiCall.family,
            func.sum(quota).label("quantidade"),
        )
        .filter(SiengeApiCall.created_at >= start_utc, SiengeApiCall.created_at < end_utc)
        .group_by(SiengeApiCall.path, SiengeApiCall.family)
        .having(func.sum(quota) > 0)
        .order_by(func.sum(quota).desc(), SiengeApiCall.path.asc())
        .limit(15)
        .all()
    )
    endpoints = [
        {"caminho": row.path, "familia": row.family, "quantidade": int(row.quantidade or 0)}
        for row in endpoint_rows
    ]
    return {
        "ano": year,
        "mes": month,
        "fuso": "America/Sao_Paulo",
        "pacote": PACKAGE_NAME,
        "historico_vazio": False,
        "familias": families,
        "endpoints": endpoints,
    }
