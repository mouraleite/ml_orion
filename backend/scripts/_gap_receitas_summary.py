"""Resumo dos gaps SP-MIG vs INC-* por bloco de categoria (somente leitura)."""
from __future__ import annotations

import os
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from sqlalchemy import extract

from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services.realizado_sienge import build_planos_maps, valor_receita_sienge


def main() -> None:
    db = SessionLocal()
    planos_id_by_name, planos_redutora = build_planos_maps(db)

    def agg(prefix: str, apply_red: bool = False) -> dict[str, float]:
        rows = (
            db.query(ActualTransaction)
            .filter(
                ActualTransaction.transaction_type == "INCOME",
                ActualTransaction.is_forecast == False,
                ActualTransaction.source_id.like(prefix),
                extract("year", ActualTransaction.transaction_date) == 2026,
                extract("month", ActualTransaction.transaction_date) <= 8,
            )
            .all()
        )
        by_cat: dict[str, float] = defaultdict(float)
        for r in rows:
            v = float(r.value or 0)
            cat = (r.category or "").strip()
            if apply_red:
                pid = planos_id_by_name.get(cat)
                if pid:
                    v = valor_receita_sienge(v, pid, cat, planos_redutora)
            by_cat[cat] += v
        return dict(by_cat)

    sp = agg("SP-MIG-%", False)
    inc = agg("INC-%", True)
    keys = set(sp) | set(inc)

    blocks = [
        ("Rendimentos", lambda k: "rendimento" in k.lower()),
        ("Descontos Obtidos", lambda k: "descontos obtidos" in k.lower()),
        ("Reembolso", lambda k: "reembolso" in k.lower()),
        (
            "Depósitos não Identificados",
            lambda k: "depósitos não" in k.lower() or "depositos nao" in k.lower(),
        ),
        ("AFAC", lambda k: k.strip().upper() == "AFAC"),
        ("Receita de Venda de Lotes", lambda k: "venda de lotes" in k.lower()),
        ("Lucros Recebidos", lambda k: "lucros recebidos" in k.lower()),
        ("Juros Ativos", lambda k: "juros ativos" in k.lower()),
    ]

    used: set[str] = set()
    print("=== BLOCO jan-ago 2026 (SP vs INC) ===")
    print(f"{'Bloco':<35} {'SP':>14} {'INC':>14} {'Diff':>14}")
    named_sp = named_inc = 0.0
    for name, pred in blocks:
        s = i = 0.0
        for k in keys:
            if k in used or not pred(k):
                continue
            s += sp.get(k, 0)
            i += inc.get(k, 0)
            used.add(k)
        d = i - s
        print(f"{name:<35} {s:14,.2f} {i:14,.2f} {d:14,.2f}")
        named_sp += s
        named_inc += i

    outros_sp = sum(v for k, v in sp.items() if k not in used)
    outros_inc = sum(v for k, v in inc.items() if k not in used)
    print(
        f"{'Outros':<35} {outros_sp:14,.2f} {outros_inc:14,.2f} {outros_inc - outros_sp:14,.2f}"
    )
    print(
        f"{'TOTAL GERAL':<35} {sum(sp.values()):14,.2f} {sum(inc.values()):14,.2f} "
        f"{sum(inc.values()) - sum(sp.values()):14,.2f}"
    )

    print("\n=== 73200 AFAC ===")
    cc = db.query(CostCenter).filter(CostCenter.id_sienge == "73200").first()
    for prefix in ["SP-MIG-%", "INC-%"]:
        rows = (
            db.query(ActualTransaction)
            .filter(
                ActualTransaction.cost_center_id == cc.id,
                ActualTransaction.category.like("%AFAC%"),
                ActualTransaction.source_id.like(prefix),
                extract("year", ActualTransaction.transaction_date) == 2026,
                extract("month", ActualTransaction.transaction_date) <= 8,
            )
            .order_by(ActualTransaction.transaction_date)
            .all()
        )
        total = sum(float(r.value or 0) for r in rows)
        print(f"{prefix} n={len(rows)} sum={total:,.2f}")

    print("\n=== Categorias SP-only (|SP|>1k, INC~0) ===")
    only_sp = []
    for k, v in sp.items():
        if abs(v) < 1000 or abs(inc.get(k, 0)) >= 1:
            continue
        only_sp.append((abs(v), k, v))
    only_sp.sort(reverse=True)
    for _, k, v in only_sp[:20]:
        print(f"{v:12,.2f}  {k}")

    db.close()


if __name__ == "__main__":
    main()
