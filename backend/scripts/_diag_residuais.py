"""Somente leitura: diagnostico dos residuais SP x OUT por CC + categoria.

Mostra, por mes: SP-MIG, OUT-* gravado e o que a API tem em cada operationType
para a mesma categoria (inclui bankMovements da categoria).

Uso: python scripts/_diag_residuais.py <CC> "<categoria>" [<CC> "<categoria>" ...]
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(".env")
sys.path.insert(0, ".")

from app.services.sienge_outcome_parse import category_rate_ratio, payment_gross_amount
from app.services.sienge_sync import SIENGE_BASE_URL, _fetch_paginated_bulk

import app.main  # noqa: F401
from sqlalchemy import extract

from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter


def api_ops(code: str, categoria: str):
    """(por_op[(op, mes)] , bm[mes], amostras)"""
    url = (
        f"{SIENGE_BASE_URL}/outcome?startDate=2026-01-01&endDate=2026-08-31"
        f"&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01"
        f"&costCentersId={code}&withAuthorizations=false&withBankMovements=true"
    )
    por_op = defaultdict(float)
    bm = defaultdict(float)
    amostras = []
    # dedupe igual ao source_id do sync (a API pagina por pagamento, nao por titulo)
    vistos: set = set()
    cat_lower = categoria.strip().lower()
    for page in _fetch_paginated_bulk(url):
        for item in page:
            bid = item.get("billId")
            cats = [
                c
                for c in (item.get("paymentsCategories") or [])
                if str(c.get("costCenterId")) == code
                and (c.get("financialCategoryName") or "").strip().lower() == cat_lower
            ]
            if not cats:
                continue
            for p in item.get("payments") or []:
                d = (p.get("paymentDate") or "")[:10]
                if not d.startswith("2026") or int(d[5:7]) > 8:
                    continue
                mes = int(d[5:7])
                op = int(p.get("operationTypeId") or 0)
                gross = payment_gross_amount(p)
                pmt_id = p.get("sequencialNumber", p.get("id", "0"))
                for c in cats:
                    chave = (bid, op, pmt_id, d, c.get("financialCategoryId"))
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    v = gross * category_rate_ratio(c)
                    por_op[(op, mes)] += v
                    if len(amostras) < 12:
                        amostras.append(
                            (
                                mes,
                                op,
                                p.get("operationTypeName"),
                                v,
                                category_rate_ratio(c),
                                bid,
                                (item.get("creditorName") or "")[:26],
                            )
                        )
                for movement in p.get("bankMovements") or []:
                    for pc in movement.get("paymentCategories") or []:
                        if str(pc.get("costCenterId")) != code:
                            continue
                        if (pc.get("financialCategoryName") or "").strip().lower() != cat_lower:
                            continue
                        chave = ("bm", bid, movement.get("id"), pc.get("financialCategoryId"))
                        if chave in vistos:
                            continue
                        vistos.add(chave)
                        bm[mes] += abs(float(movement.get("amount") or 0)) * category_rate_ratio(pc)
    return por_op, bm, amostras


def main(pares: list[tuple[str, str]]):
    db = SessionLocal()
    for code, categoria in pares:
        cc = db.query(CostCenter).filter(CostCenter.id_sienge == code).first()
        if not cc:
            print(f"CC {code} nao encontrado")
            continue
        sp = defaultdict(float)
        out = defaultdict(float)
        for r in (
            db.query(ActualTransaction)
            .filter(
                ActualTransaction.cost_center_id == cc.id,
                ActualTransaction.transaction_type == "OUTCOME",
                ActualTransaction.is_forecast == False,  # noqa: E712
                extract("year", ActualTransaction.transaction_date) == 2026,
                extract("month", ActualTransaction.transaction_date) <= 8,
            )
            .all()
        ):
            if (r.category or "").strip().lower() != categoria.strip().lower():
                continue
            sid = r.source_id or ""
            if sid.startswith("SP-MIG-"):
                sp[r.transaction_date.month] += float(r.value or 0)
            elif sid.startswith("OUT-"):
                out[r.transaction_date.month] += float(r.value or 0)

        por_op, bm, amostras = api_ops(code, categoria)
        ops = sorted({op for op, _ in por_op})

        print(f"=== CC {code} | {categoria} ===")
        header = f"{'mes':>3} {'SP':>12} {'OUT':>12}" + "".join(f"{'op' + str(o):>12}" for o in ops)
        if bm:
            header += f"{'BM':>12}"
        print(header)
        tot = defaultdict(float)
        for mes in range(1, 9):
            row = f"{mes:>3} {sp.get(mes, 0.0):12,.0f} {out.get(mes, 0.0):12,.0f}"
            for o in ops:
                row += f"{por_op.get((o, mes), 0.0):12,.0f}"
                tot[o] += por_op.get((o, mes), 0.0)
            if bm:
                row += f"{bm.get(mes, 0.0):12,.0f}"
                tot["bm"] += bm.get(mes, 0.0)
            tot["sp"] += sp.get(mes, 0.0)
            tot["out"] += out.get(mes, 0.0)
            print(row)
        row = f"{'TOT':>3} {tot['sp']:12,.0f} {tot['out']:12,.0f}"
        for o in ops:
            row += f"{tot[o]:12,.0f}"
        if bm:
            row += f"{tot['bm']:12,.0f}"
        print(row)
        print(f"  gap (OUT-SP): {tot['out'] - tot['sp']:,.2f}")
        if amostras:
            print("  amostras:")
            for mes, op, nome, v, rate, bid, cred in amostras:
                print(f"    m{mes} op{op} {str(nome)[:22]:22} {v:12,.2f} rate={rate:.2f} bill={bid} {cred}")
        print()
    db.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    pares = [(args[i], args[i + 1]) for i in range(0, len(args) - 1, 2)]
    main(pares)
