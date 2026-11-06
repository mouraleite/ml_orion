"""Persiste o 31/12 fechado de contas B+I+C. Não entra no GET do DFC."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.sienge_account_balance import SiengeAccountBalance
from app.services.geracao_caixa import (
    TIPOS_CAIXA,
    anos_fechados_snapshot,
    eh_conta_caixa,
    eh_mutuo,
    tipo_conta,
)
from app.services.mldu_ownership import effective_for_company
from app.services.sienge_client import get_default_client

logger = logging.getLogger(__name__)

_PAGE_LIMIT = 100
_MAX_PAGES = 40
_PAGE_SLEEP = 0.4
_PAGE_FAILS = 3


def _collect_v1(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Pagina até resultados vazios. Página com erro não encerra a coleta."""
    offset = 0
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    fails = 0
    for _ in range(_MAX_PAGES):
        qs = urlencode({**params, "limit": _PAGE_LIMIT, "offset": offset})
        url = f"{client.api_v1_base_url}{path}?{qs}"
        data = client.get_json(url, timeout=90, retries=4)
        if not data:
            fails += 1
            logger.warning("snapshot caixa: falha %s/%s em %s offset=%s", fails, _PAGE_FAILS, path, offset)
            if fails >= _PAGE_FAILS:
                break
            time.sleep(1.5 * fails)
            continue
        fails = 0
        if isinstance(data, list):
            page = data
        else:
            page = data.get("results") or data.get("data") or []
        if not page:
            break
        new_rows = 0
        for row in page:
            if not isinstance(row, dict):
                continue
            key = (
                str(row.get("companyId") or "").strip(),
                str(row.get("accountNumber") or "").strip(),
                str(row.get("balanceDate") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
            new_rows += 1
        if new_rows == 0:
            break
        offset += len(page)
        # Com flag S o count é o cadastro (~172), não o tamanho da página.
        # Página curta não significa fim — só lista vazia ou página repetida.
        time.sleep(_PAGE_SLEEP)
    logger.info("snapshot caixa: %s → %s linhas", path, len(rows))
    return rows


def mapa_tipos_contas(client) -> dict[tuple[str, str], dict[str, str]]:
    rows = _collect_v1(client, "/checking-accounts", {})
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        cid = str(row.get("companyId") or "").strip()
        acc = str(row.get("accountNumber") or "").strip()
        if not cid or not acc:
            continue
        out[(cid, acc)] = {
            "account_type": tipo_conta(row.get("accountType")),
            "account_name": str(row.get("accountName") or "").strip(),
        }
    return out


def persist_closed_year_balances(db: Session, *, hoje: date | datetime | None = None) -> dict[str, Any]:
    years = anos_fechados_snapshot(hoje)
    if not years:
        return {"ok": True, "anos": []}
    if not (settings.SIENGE_PASS or "").strip():
        logger.warning("snapshot caixa: SIENGE_PASS vazio")
        return {"ok": False, "error": "sem credencial", "anos": []}

    client = get_default_client()
    tipos = mapa_tipos_contas(client)
    if not tipos:
        logger.warning("snapshot caixa: cadastro de contas vazio")
    agora = datetime.utcnow()
    resumo: list[dict[str, Any]] = []

    for year in years:
        balance_date = date(year, 12, 31)
        raw = _collect_v1(
            client,
            "/accounts-balances",
            {
                "balanceDate": balance_date.isoformat(),
                "showLastBalanceIfNotExistBalance": "S",
            },
        )
        if not raw:
            logger.warning("snapshot caixa: sem linhas para 31/12/%s — mantém o que já existe", year)
            resumo.append({"ano": year, "n": 0, "skipped": True})
            continue
        kept: list[SiengeAccountBalance] = []
        for row in raw:
            cid = str(row.get("companyId") or "").strip()
            acc = str(row.get("accountNumber") or "").strip()
            if not cid or not acc:
                continue
            meta = tipos.get((cid, acc), {})
            t = tipo_conta(row.get("accountType")) or meta.get("account_type") or ""
            nome = str(row.get("accountName") or meta.get("account_name") or "").strip()
            cand = {
                "account_type": t,
                "accountType": t,
                "account_name": nome,
                "accountName": nome,
                "account_number": acc,
                "accountNumber": acc,
                "amount": row.get("amount"),
            }
            if not eh_conta_caixa(cand):
                continue
            amount = row.get("amount")
            if amount is None:
                continue
            kept.append(
                SiengeAccountBalance(
                    company_id_sienge=cid,
                    account_number=acc,
                    account_name=nome or None,
                    account_type=t,
                    balance_date=balance_date,
                    amount=float(amount),
                    synced_at=agora,
                )
            )
        if not kept:
            logger.warning("snapshot caixa: 0 contas B+I+C em 31/12/%s — não apaga snapshot anterior", year)
            resumo.append({"ano": year, "n": 0, "skipped": True})
            continue
        db.query(SiengeAccountBalance).filter(SiengeAccountBalance.balance_date == balance_date).delete()
        for item in kept:
            db.add(item)
        db.commit()
        resumo.append({"ano": year, "n": len(kept)})
        logger.info("snapshot caixa 31/12/%s: %s contas B+I+C", year, len(kept))

    return {"ok": True, "anos": resumo}


def _pct_mldu(company: Optional[Company]) -> float:
    if company is None:
        return 0.0
    return float(effective_for_company(company) or 0.0) / 100.0


def saldos_31_12(
    db: Session,
    *,
    ids_empresa: Optional[list[str]] = None,
    mldu: bool = False,
) -> dict[int, float]:
    """Ano do 31/12 → soma B+I+C. ids_empresa = id Sienge; None = todas."""
    q = db.query(SiengeAccountBalance).filter(SiengeAccountBalance.account_type.in_(tuple(TIPOS_CAIXA)))
    if ids_empresa:
        q = q.filter(SiengeAccountBalance.company_id_sienge.in_(ids_empresa))
    rows = q.all()
    empresas: dict[str, Company] = {}
    if mldu:
        empresas = {
            str(c.id_sienge).strip(): c
            for c in db.query(Company).all()
            if c.id_sienge
        }
    out: dict[int, float] = {}
    for row in rows:
        if eh_mutuo(tipo=row.account_type, nome=row.account_name, numero=row.account_number):
            continue
        year = row.balance_date.year
        amount = float(row.amount or 0.0)
        if mldu:
            amount *= _pct_mldu(empresas.get(str(row.company_id_sienge)))
        out[year] = out.get(year, 0.0) + amount
    return out
