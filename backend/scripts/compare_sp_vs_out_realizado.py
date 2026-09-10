"""
Cruzamento somente leitura: Realizado SharePoint (SP-MIG) × Sienge pago (OUT-*).
Despesas (OUTCOME), por centro de custo + plano financeiro + mês.

Não altera orçamento, forecast nem actual_transactions.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Dict, Tuple

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from sqlalchemy import extract

from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.services.realizado_sienge import build_planos_maps, valor_despesa_sienge

Key = Tuple[int, str, int]  # cc_id, plano_nome, mes (1-12)
TOL = 1.0  # R$ 1 — ruído de arredondamento


def _agg_sp(db, ano: int) -> Dict[Key, float]:
    rows = (
        db.query(ActualTransaction)
        .filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("SP-MIG-%"),
            extract("year", ActualTransaction.transaction_date) == ano,
        )
        .all()
    )
    out: Dict[Key, float] = defaultdict(float)
    for r in rows:
        if not r.transaction_date:
            continue
        nome = (r.category or "").strip()
        out[(r.cost_center_id, nome, r.transaction_date.month)] += float(r.value or 0)
    return out


def _agg_out(db, ano: int) -> Dict[Key, float]:
    planos_id_by_name, planos_redutora = build_planos_maps(db)
    rows = (
        db.query(ActualTransaction)
        .filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("OUT-%"),
            extract("year", ActualTransaction.transaction_date) == ano,
        )
        .all()
    )
    out: Dict[Key, float] = defaultdict(float)
    for r in rows:
        if not r.transaction_date:
            continue
        nome = (r.category or "").strip()
        plano_id = planos_id_by_name.get(nome)
        if not plano_id:
            # mantém nome mesmo sem plano mapeado (aparece no relatório)
            val = float(r.value or 0)
        else:
            val = valor_despesa_sienge(float(r.value or 0), plano_id, nome, planos_redutora)
        out[(r.cost_center_id, nome, r.transaction_date.month)] += val
    return out


def main(ano: int = 2026, top_n: int = 40):
    db = SessionLocal()
    try:
        ccs = {c.id: c for c in db.query(CostCenter).all()}
        sp = _agg_sp(db, ano)
        out = _agg_out(db, ano)

        keys = set(sp) | set(out)
        diffs = []
        for k in keys:
            v_sp = sp.get(k, 0.0)
            v_out = out.get(k, 0.0)
            delta = v_out - v_sp
            if abs(delta) < TOL and abs(v_sp) < TOL and abs(v_out) < TOL:
                continue
            diffs.append((abs(delta), delta, k, v_sp, v_out))

        diffs.sort(reverse=True, key=lambda x: x[0])

        total_sp = sum(sp.values())
        total_out = sum(out.values())
        only_sp = sum(1 for k in sp if k not in out)
        only_out = sum(1 for k in out if k not in sp)
        match = sum(
            1
            for k in keys
            if abs(sp.get(k, 0) - out.get(k, 0)) < TOL and (abs(sp.get(k, 0)) >= TOL or abs(out.get(k, 0)) >= TOL)
        )
        diverge = sum(1 for _, delta, *_ in diffs if abs(delta) >= TOL)

        print("=" * 72)
        print(f"Cruzamento Realizado DESPESAS {ano}: SharePoint (SP-MIG) × Sienge (OUT-*)")
        print("=" * 72)
        print(f"Linhas SP-MIG (CC×plano×mês): {len(sp)}")
        print(f"Linhas OUT-*  (CC×plano×mês): {len(out)}")
        print(f"Só no SharePoint: {only_sp} | Só no Sienge OUT: {only_out}")
        print(f"Batendo (|d|<{TOL}): {match} | Divergindo: {diverge}")
        print(f"Total SP-MIG: R$ {total_sp:,.2f}")
        print(f"Total OUT-*:  R$ {total_out:,.2f}")
        print(f"Diff (OUT - SP): R$ {total_out - total_sp:,.2f}")
        print()
        print(f"Top {top_n} maiores diferencas absolutas:")
        print("-" * 72)
        print(f"{'d R$':>14} {'SP-MIG':>14} {'OUT-*':>14}  {'mes':>3}  CC / Plano")
        for abs_d, delta, (cc_id, plano, mes), v_sp, v_out in diffs[:top_n]:
            cc = ccs.get(cc_id)
            cc_label = f"{cc.id_sienge or '?'} {getattr(cc, 'nome', None) or getattr(cc, 'name', '')}" if cc else f"id={cc_id}"
            print(
                f"{delta:14,.2f} {v_sp:14,.2f} {v_out:14,.2f}  {mes:3d}  "
                f"{cc_label[:40]} | {plano[:40]}"
            )

        # Totais por CC
        by_cc_sp: Dict[int, float] = defaultdict(float)
        by_cc_out: Dict[int, float] = defaultdict(float)
        for (cc_id, _, _), v in sp.items():
            by_cc_sp[cc_id] += v
        for (cc_id, _, _), v in out.items():
            by_cc_out[cc_id] += v
        cc_diffs = []
        for cc_id in set(by_cc_sp) | set(by_cc_out):
            d = by_cc_out.get(cc_id, 0) - by_cc_sp.get(cc_id, 0)
            cc_diffs.append((abs(d), d, cc_id, by_cc_sp.get(cc_id, 0), by_cc_out.get(cc_id, 0)))
        cc_diffs.sort(reverse=True)

        print()
        print(f"Top 20 CCs por |d| total anual:")
        print("-" * 72)
        for abs_d, delta, cc_id, v_sp, v_out in cc_diffs[:20]:
            cc = ccs.get(cc_id)
            label = f"{cc.id_sienge or '?'} - {getattr(cc, 'nome', None) or getattr(cc, 'name', '')}" if cc else str(cc_id)
            print(f"{delta:14,.2f}  SP={v_sp:14,.2f}  OUT={v_out:14,.2f}  {label[:55]}")
    finally:
        db.close()


if __name__ == "__main__":
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    main(ano=ano)
