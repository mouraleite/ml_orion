"""
Recarrega o realizado Sienge desde a implantação (ago/2016) até 2025.

Etapas (nessa ordem): receitas → vendas → despesas.
Não altera o sync diário nem fórmulas. A API é lida por completo ANTES
de gravar: se a Sienge falhar, o banco permanece como estava.

Fatia: tenta o ano inteiro; se a API estourar timeout, cai para mês.
Empresas: todos os centros com id_sienge, agrupados por __id_empresa.

  python scripts/backfill_sienge_historico.py --etapa receitas
  python scripts/backfill_sienge_historico.py --etapa receitas --empresa 6 --start 2025-01-01 --end 2025-01-31
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.backfill", override=True)

from sqlalchemy import or_  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.models.actual_transaction import ActualTransaction  # noqa: E402
from app.models.cost_center import CostCenter  # noqa: E402
from app.services.sienge_client import bulk_base_url, get_default_client  # noqa: E402
from app.services.sienge_income_parse import iter_income_bank_lines  # noqa: E402
from app.services.sienge_outcome_parse import iter_outcome_realizado_lines  # noqa: E402
from app.services.sienge_sync import (  # noqa: E402
    mirror_afac_income_as_outcome,
    outcome_contas_pagar_url,
    sync_sales,
    sync_units,
)

START_IMPLANTACAO = date(2016, 8, 1)
END_HISTORICO = date(2025, 12, 31)
PAGE_LIMIT = 200
TIMEOUT_S = 120
RETRIES = 4
SLEEP_S = 0.15
STATE_PATH = ROOT / "scratch" / "backfill_sienge_state.json"


class FetchError(Exception):
    """Falha de rede/API: não gravar nada neste recorte."""


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with (STATE_PATH.parent / "backfill_sienge.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"done": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"done": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _key(etapa: str, cc: str, start: str, end: str) -> str:
    return f"{etapa}|{cc}|{start}|{end}"


def month_windows(start: date, end: date) -> list[tuple[date, date]]:
    out = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        last = calendar.monthrange(y, m)[1]
        w0 = max(start, date(y, m, 1))
        w1 = min(end, date(y, m, last))
        out.append((w0, w1))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def year_windows(start: date, end: date) -> list[tuple[date, date]]:
    out = []
    for y in range(start.year, end.year + 1):
        w0 = max(start, date(y, 1, 1))
        w1 = min(end, date(y, 12, 31))
        out.append((w0, w1))
    return out


def paginate_strict(url: str, headers: dict) -> list[dict]:
    """Todas as páginas ou exceção. Não trata erro como lista vazia."""
    offset = 0
    pages: list[dict] = []
    seen: set = set()
    while True:
        sep = "&" if "?" in url else "?"
        paged = f"{url}{sep}limit={PAGE_LIMIT}&offset={offset}"
        data = _get_json_raise(paged, headers)
        results = data.get("data") or data.get("results") or []
        if not results:
            break
        first = results[0]
        marker = first.get("id") or f"{first.get('billId')}-{first.get('installmentId')}"
        if marker in seen:
            break
        seen.add(marker)
        pages.extend(results)
        if len(results) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
        time.sleep(SLEEP_S)
    return pages


def _get_json_raise(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                if resp.status != 200:
                    raise FetchError(f"HTTP {resp.status} {url}")
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (401, 403):
                raise FetchError(f"HTTP {exc.code} auth {url}") from exc
            if exc.code == 404:
                return {"data": []}
            _log(f"  HTTP {exc.code} tentativa {attempt}/{RETRIES}")
            time.sleep(min(30, 2 ** attempt))
        except Exception as exc:
            last_err = exc
            _log(f"  erro {type(exc).__name__}: {exc} tentativa {attempt}/{RETRIES}")
            time.sleep(min(30, 2 ** attempt))
    raise FetchError(f"falhou após {RETRIES} tentativas: {last_err}")


def _income_url(cc_sienge: str, start: str, end: str) -> str:
    return (
        f"{bulk_base_url()}/income?startDate={start}&endDate={end}"
        f"&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01"
        f"&costCentersId={cc_sienge}&withAuthorizations=false&withBankMovements=true"
    )


def fetch_income_lines(headers: dict, cc_sienge: str, start: str, end: str) -> list[dict]:
    items = paginate_strict(_income_url(cc_sienge, start, end), headers)
    lines = []
    for item in items:
        lines.extend(iter_income_bank_lines(item, cc_sienge))
    return lines


def apply_income(db: Session, cc: CostCenter, start: date, end: date, lines: list[dict]) -> int:
    """Apaga INC-* / OUT-TARIFA-* do recorte só depois da busca ok."""
    db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id == cc.id,
        ActualTransaction.is_forecast == False,  # noqa: E712
        ActualTransaction.transaction_date >= start,
        ActualTransaction.transaction_date <= end,
        or_(
            ActualTransaction.source_id.like("INC-%"),
            ActualTransaction.source_id.like("OUT-TARIFA-%"),
        ),
    ).delete(synchronize_session=False)
    db.flush()

    existing = {
        r.source_id: r
        for r in db.query(ActualTransaction)
        .filter(
            ActualTransaction.cost_center_id == cc.id,
            or_(
                ActualTransaction.source_id.like("INC-%"),
                ActualTransaction.source_id.like("OUT-TARIFA-%"),
            ),
        )
        .all()
        if r.source_id
    }
    n = 0
    for line in lines:
        try:
            dtx = datetime.strptime(str(line["payment_date"])[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        source_id = line["source_id"]
        record = existing.get(source_id)
        if not record:
            record = ActualTransaction(
                cost_center_id=cc.id,
                source_id=source_id,
                transaction_type=line["transaction_type"],
            )
            db.add(record)
            existing[source_id] = record
        record.transaction_type = line["transaction_type"]
        record.transaction_date = dtx
        record.value = line["value"]
        record.category = line["category_name"]
        record.bill_id = str(line["bill_id"]) if line.get("bill_id") else None
        record.creditor_name = line.get("creditor_name")
        record.document_name = line.get("document_name")
        record.document_number = line.get("document_number")
        record.is_forecast = False
        n += 1
    db.commit()
    mirror_afac_income_as_outcome(db, cc, start.isoformat(), end.isoformat())
    return n


def fetch_outcome_lines(headers: dict, cc_sienge: str, start: str, end: str) -> list[dict]:
    url = outcome_contas_pagar_url(cc_sienge, start, end)
    items = paginate_strict(url, headers)
    lines = []
    for item in items:
        lines.extend(iter_outcome_realizado_lines(item, cc_sienge))
    return lines


def apply_outcome_op1(db: Session, cc: CostCenter, start: date, end: date, lines: list[dict]) -> int:
    """Grava OP1/OP8/OP10/RET. Não apaga PMT legado (acompanhamento de obra)."""
    db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id == cc.id,
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast == False,  # noqa: E712
        ActualTransaction.transaction_date >= start,
        ActualTransaction.transaction_date <= end,
        or_(
            ActualTransaction.source_id.like("OUT-%-OP1-%"),
            ActualTransaction.source_id.like("OUT-%-OP8-%"),
            ActualTransaction.source_id.like("OUT-%-OP10-%"),
            ActualTransaction.source_id.like("OUT-%-RET-%"),
        ),
    ).delete(synchronize_session=False)
    db.flush()

    existing = {
        r.source_id: r
        for r in db.query(ActualTransaction)
        .filter(
            ActualTransaction.cost_center_id == cc.id,
            ActualTransaction.transaction_type == "OUTCOME",
            or_(
                ActualTransaction.source_id.like("OUT-%-OP1-%"),
                ActualTransaction.source_id.like("OUT-%-OP8-%"),
                ActualTransaction.source_id.like("OUT-%-OP10-%"),
                ActualTransaction.source_id.like("OUT-%-RET-%"),
            ),
        )
        .all()
        if r.source_id
    }
    n = 0
    for line in lines:
        try:
            dtx = datetime.strptime(str(line["payment_date"])[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        source_id = line["source_id"]
        record = existing.get(source_id)
        if not record:
            record = ActualTransaction(
                cost_center_id=cc.id,
                source_id=source_id,
                transaction_type="OUTCOME",
            )
            db.add(record)
            existing[source_id] = record
        record.transaction_date = dtx
        record.value = line["value"]
        record.category = line["category_name"]
        record.bill_id = str(line["bill_id"]) if line.get("bill_id") else None
        record.creditor_name = line.get("creditor_name")
        record.document_name = line.get("document_name")
        record.document_number = line.get("document_number")
        record.authorization_name = line.get("authorization_name")
        record.is_forecast = False
        n += 1
    db.commit()
    return n


def list_ccs(db: Session, empresa_id: str | None, cc_filter: set[str] | None) -> list[CostCenter]:
    q = db.query(CostCenter).filter(
        CostCenter.id_sienge.isnot(None),
        CostCenter.id_sienge != "",
    )
    rows = q.order_by(CostCenter.id_sienge).all()
    out = []
    for cc in rows:
        if cc_filter and str(cc.id_sienge) not in cc_filter:
            continue
        data = cc.custom_data or {}
        emp = str(data.get("__id_empresa") or "")
        if empresa_id and emp != str(empresa_id):
            continue
        out.append(cc)
    return out


def empresa_nome(cc: CostCenter) -> str:
    data = cc.custom_data or {}
    return str(data.get("__nome_empresa") or "").strip() or "(sem empresa)"


def _db_retry(fn, retries: int = 4):
    """Sessão nova a cada gravação — o pooler do Neon corta conexão ociosa."""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        db = SessionLocal()
        try:
            return fn(db)
        except OperationalError as exc:
            last = exc
            _log(f"  conexão Neon caiu (tentativa {attempt}/{retries})")
            try:
                db.rollback()
            except Exception:
                pass
            time.sleep(min(30, 2 ** attempt))
            try:
                from app.db.database import engine

                engine.dispose()
            except Exception:
                pass
        finally:
            db.close()
    raise FetchError(f"Neon indisponível: {last}") from last


def run_income_window(headers: dict, cc_id: int, cc_sienge: str, start: date, end: date) -> int:
    lines = fetch_income_lines(headers, cc_sienge, start.isoformat(), end.isoformat())

    def _apply(db: Session) -> int:
        cc = db.get(CostCenter, cc_id)
        if cc is None:
            raise FetchError(f"CC id={cc_id} sumiu")
        return apply_income(db, cc, start, end, lines)

    return _db_retry(_apply)


def run_outcome_window(headers: dict, cc_id: int, cc_sienge: str, start: date, end: date) -> int:
    lines = fetch_outcome_lines(headers, cc_sienge, start.isoformat(), end.isoformat())

    def _apply(db: Session) -> int:
        cc = db.get(CostCenter, cc_id)
        if cc is None:
            raise FetchError(f"CC id={cc_id} sumiu")
        return apply_outcome_op1(db, cc, start, end, lines)

    return _db_retry(_apply)


def sync_with_fallback(
    headers: dict,
    cc_id: int,
    cc_sienge: str,
    start: date,
    end: date,
    runner,
    state: dict,
    etapa: str,
    force: bool,
) -> tuple[int, int]:
    """Tenta o recorte inteiro; se falhar, quebra em meses. Retorna (ok_windows, linhas)."""
    done = state.setdefault("done", {})
    yk = _key(etapa, cc_sienge, start.isoformat(), end.isoformat())
    if done.get(yk) and not force:
        return 0, int(done[yk].get("n") or 0)

    try:
        n = runner(headers, cc_id, cc_sienge, start, end)
        done[yk] = {"n": n, "modo": "ano", "ts": datetime.now().isoformat(timespec="seconds")}
        _save_state(state)
        return 1, n
    except FetchError as exc:
        _log(f"  ano falhou ({exc}); quebrando em meses")

    total = 0
    ok = 0
    months = month_windows(start, end)
    for w0, w1 in months:
        mk = _key(etapa, cc_sienge, w0.isoformat(), w1.isoformat())
        if done.get(mk) and not force:
            total += int(done[mk].get("n") or 0)
            ok += 1
            continue
        try:
            n = runner(headers, cc_id, cc_sienge, w0, w1)
            done[mk] = {"n": n, "modo": "mes", "ts": datetime.now().isoformat(timespec="seconds")}
            _save_state(state)
            total += n
            ok += 1
            _log(f"    {cc_sienge} {w0}..{w1} linhas={n}")
        except FetchError as exc:
            _log(f"    FALHA {cc_sienge} {w0}..{w1}: {exc}")
    if ok == len(months):
        done[yk] = {"n": total, "modo": "meses", "ts": datetime.now().isoformat(timespec="seconds")}
        _save_state(state)
    return ok, total


def _cc_rows(ccs: list[CostCenter]) -> list[tuple[int, str, str, str]]:
    return [(cc.id, str(cc.id_sienge), cc.nome or "", empresa_nome(cc)) for cc in ccs]


def etapa_receitas(ccs: list[CostCenter], start: date, end: date, force: bool) -> None:
    client = get_default_client()
    if not (client.password or "").strip():
        raise SystemExit("SIENGE_PASS vazio. Preencha backend/.env.backfill")
    headers = {**client.auth_headers(), "Accept": "application/json"}
    state = _load_state()
    tot = 0
    rows = _cc_rows(ccs)
    for i, (cc_id, sid, nome, emp) in enumerate(rows, 1):
        _log(f"[receitas {i}/{len(rows)}] {sid} {nome} | {emp}")
        for w0, w1 in year_windows(start, end):
            try:
                _, n = sync_with_fallback(
                    headers, cc_id, sid, w0, w1, run_income_window, state, "receitas", force
                )
            except Exception as exc:
                _log(f"  FALHA {sid} {w0.year}: {exc}")
                n = 0
            tot += n
            _log(f"  {w0.year}: {n} linhas")
    _log(f"[receitas] concluido linhas_aplicadas={tot}")


def etapa_vendas(ccs: list[CostCenter], start: date, end: date, force: bool) -> None:
    state = _load_state()
    done = state.setdefault("done", {})
    rows = _cc_rows(ccs)
    for i, (cc_id, sid, nome, _emp) in enumerate(rows, 1):
        k = _key("vendas", sid, start.isoformat(), end.isoformat())
        if done.get(k) and not force:
            continue
        _log(f"[vendas {i}/{len(rows)}] {sid} {nome}")

        def _run(db: Session) -> int:
            cc = db.get(CostCenter, cc_id)
            if cc is None:
                raise FetchError(f"CC {sid} sumiu")
            sync_units(db, cc)
            sync_sales(db, cc, start.isoformat(), end.isoformat())
            return 1

        try:
            _db_retry(_run)
            done[k] = {"n": 1, "ts": datetime.now().isoformat(timespec="seconds")}
            _save_state(state)
        except Exception as exc:
            _log(f"  FALHA vendas {sid}: {exc}")
    _log("[vendas] concluido")


def etapa_despesas(ccs: list[CostCenter], start: date, end: date, force: bool) -> None:
    client = get_default_client()
    if not (client.password or "").strip():
        raise SystemExit("SIENGE_PASS vazio. Preencha backend/.env.backfill")
    headers = {**client.auth_headers(), "Accept": "application/json"}
    state = _load_state()
    tot = 0
    rows = _cc_rows(ccs)
    for i, (cc_id, sid, nome, _emp) in enumerate(rows, 1):
        _log(f"[despesas {i}/{len(rows)}] {sid} {nome}")
        for w0, w1 in year_windows(start, end):
            try:
                _, n = sync_with_fallback(
                    headers, cc_id, sid, w0, w1, run_outcome_window, state, "despesas", force
                )
            except Exception as exc:
                _log(f"  FALHA {sid} {w0.year}: {exc}")
                n = 0
            tot += n
            _log(f"  {w0.year}: {n} linhas")
    _log(f"[despesas] concluido linhas_aplicadas={tot}")


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill histórico Sienge 2016→2025")
    parser.add_argument("--etapa", choices=["receitas", "vendas", "despesas", "tudo"], required=True)
    parser.add_argument("--start", default=START_IMPLANTACAO.isoformat())
    parser.add_argument("--end", default=END_HISTORICO.isoformat())
    parser.add_argument("--empresa", default=None, help="__id_empresa Sienge (ex: 6 = Araçari SPE)")
    parser.add_argument("--cc", default=None, help="ids Sienge separados por vírgula")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end)
    cc_filter = {x.strip() for x in args.cc.split(",")} if args.cc else None

    db = SessionLocal()
    try:
        ccs = list_ccs(db, args.empresa, cc_filter)
    finally:
        db.close()

    _log(
        f"Inicio etapa={args.etapa} ccs={len(ccs)} {start}..{end} "
        f"db={os.environ.get('DATABASE_URL', '')[:32]}..."
    )
    if not ccs:
        raise SystemExit("Nenhum centro de custo no filtro.")
    if args.etapa in ("receitas", "tudo"):
        etapa_receitas(ccs, start, end, args.force)
    if args.etapa in ("vendas", "tudo"):
        etapa_vendas(ccs, start, end, args.force)
    if args.etapa in ("despesas", "tudo"):
        etapa_despesas(ccs, start, end, args.force)


if __name__ == "__main__":
    main()
