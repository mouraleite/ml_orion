"""
Cruzamento somente leitura: Realizado SharePoint (SP-MIG INCOME) × Sienge (INC-* + BM-*).
Receitas, por centro de custo + plano financeiro + mês.
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
from app.services.realizado_sienge import (
    build_planos_maps,
    categoria_excluida_receita_realizado,
    valor_receita_sienge,
)

Key = Tuple[int, str, int]  # cc_id, plano_nome, mes
TOL = 1.0


def _agg(db, ano: int, prefix: str, apply_redutora: bool) -> Dict[Key, float]:
    rows = (
        db.query(ActualTransaction)
        .filter(
            ActualTransaction.transaction_type == "INCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like(prefix),
            extract("year", ActualTransaction.transaction_date) == ano,
        )
        .all()
    )
    planos_id_by_name, planos_redutora = build_planos_maps(db)
    out: Dict[Key, float] = defaultdict(float)
    for r in rows:
        if not r.transaction_date:
            continue
        nome = (r.category or "").strip()
        if categoria_excluida_receita_realizado(nome):
            continue
        val = float(r.value or 0)
        if apply_redutora:
            pid = planos_id_by_name.get(nome)
            if pid:
                val = valor_receita_sienge(val, pid, nome, planos_redutora)
        out[(r.cost_center_id, nome, r.transaction_date.month)] += val
    return out


def main(ano: int = 2026, top_n: int = 40, max_mes: int = 8):
    db = SessionLocal()
    try:
        ccs = {c.id: c for c in db.query(CostCenter).all()}
        sp = {k: v for k, v in _agg(db, ano, "SP-MIG-%", False).items() if k[2] <= max_mes}
        inc = {k: v for k, v in _agg(db, ano, "INC-%", True).items() if k[2] <= max_mes}
        bm = {k: v for k, v in _agg(db, ano, "BM-%", True).items() if k[2] <= max_mes}
        sienge: Dict[Key, float] = defaultdict(float)
        for k, v in inc.items():
            sienge[k] += v
        for k, v in bm.items():
            sienge[k] += v

        keys = set(sp) | set(sienge)
        diffs = []
        for k in keys:
            v_sp = sp.get(k, 0.0)
            v_si = sienge.get(k, 0.0)
            delta = v_si - v_sp
            if abs(delta) < TOL and abs(v_sp) < TOL and abs(v_si) < TOL:
                continue
            diffs.append((abs(delta), delta, k, v_sp, v_si))
        diffs.sort(reverse=True, key=lambda x: x[0])

        total_sp = sum(sp.values())
        total_sienge = sum(sienge.values())
        only_sp = sum(1 for k in sp if k not in sienge)
        only_sienge = sum(1 for k in sienge if k not in sp)
        match = sum(
            1
            for k in keys
            if abs(sp.get(k, 0) - sienge.get(k, 0)) < TOL
            and (abs(sp.get(k, 0)) >= TOL or abs(sienge.get(k, 0)) >= TOL)
        )
        diverge = sum(1 for _, delta, *_ in diffs if abs(delta) >= TOL)

        print("=" * 72)
        print(f"Cruzamento Realizado RECEITAS {ano} (mes<= {max_mes}): SP-MIG x INC+BM")
        print("=" * 72)
        print(f"Linhas SP-MIG: {len(sp)} | Linhas Sienge (INC+BM): {len(sienge)}")
        print(f"So no SharePoint: {only_sp} | So no Sienge: {only_sienge}")
        print(f"Batendo (|d|<{TOL}): {match} | Divergindo: {diverge}")
        print(f"Total SP-MIG: R$ {total_sp:,.2f}")
        print(f"Total INC+BM: R$ {total_sienge:,.2f}")
        print(f"Diff (Sienge - SP): R$ {total_sienge - total_sp:,.2f}")
        print()
        print(f"Top {top_n} maiores diferencas:")
        print("-" * 72)
        for abs_d, delta, (cc_id, plano, mes), v_sp, v_si in diffs[:top_n]:
            cc = ccs.get(cc_id)
            label = f"{getattr(cc, 'id_sienge', '?')} {getattr(cc, 'nome', '')}" if cc else str(cc_id)
            print(
                f"{delta:14,.2f} SP={v_sp:12,.2f} SIE={v_si:12,.2f}  "
                f"m={mes:02d}  {label[:38]} | {plano[:36]}"
            )

        by_cc_sp: Dict[int, float] = defaultdict(float)
        by_cc_si: Dict[int, float] = defaultdict(float)
        for (cc_id, _, _), v in sp.items():
            by_cc_sp[cc_id] += v
        for (cc_id, _, _), v in sienge.items():
            by_cc_si[cc_id] += v
        cc_diffs = []
        for cc_id in set(by_cc_sp) | set(by_cc_si):
            d = by_cc_si.get(cc_id, 0) - by_cc_sp.get(cc_id, 0)
            cc_diffs.append((abs(d), d, cc_id, by_cc_sp.get(cc_id, 0), by_cc_si.get(cc_id, 0)))
        cc_diffs.sort(reverse=True)
        print()
        print("Top 20 CCs por |d|:")
        for abs_d, delta, cc_id, v_sp, v_si in cc_diffs[:20]:
            cc = ccs.get(cc_id)
            label = f"{getattr(cc, 'id_sienge', '?')} - {getattr(cc, 'nome', '')}" if cc else str(cc_id)
            print(f"{delta:14,.2f}  SP={v_sp:14,.2f}  SIE={v_si:14,.2f}  {label[:55]}")
    finally:
        db.close()


if __name__ == "__main__":
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    main(ano=ano)
