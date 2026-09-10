"""Somente leitura: ancoras de conferencia SP-MIG x Sienge (jan-ago/2026).

Estado da reconciliacao e residuos conhecidos: docs/conferencia-realizado-sp-mig.md
Antes de investigar Adiantamento a Parceiros / Adiantamentos a Fornecedores,
leia a nota tecnica desse documento: a diferenca e' conceitual, nao e' erro.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(".env")
sys.path.insert(0, ".")

import app.main  # noqa: F401
from sqlalchemy import extract

from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services.realizado_sienge import build_planos_maps, valor_despesa_sienge

CATEGORIAS = [
    "Distratos",
    "Distratos Permuta/Quitação",
    "IPTU/ ITR e Outros Impostos",
    "ISS",
    "Documentos / Multas e Seguros de Veículos",
    "Materiais de Limpeza e Copa",
    "Serviços de Terceiros (Obra)",
    "Adiantamento a Parceiros",
    "Adiantamentos a Fornecedores",
]
CCS = ["72801", "73200"]


def main():
    db = SessionLocal()
    cc_nome = {c.id: str(c.id_sienge) for c in db.query(CostCenter).all()}

    sp_cat = defaultdict(float)
    out_cat = defaultdict(float)
    sp_cc = defaultdict(float)
    out_cc = defaultdict(float)
    sp_afac = out_afac = 0.0

    for r in (
        db.query(ActualTransaction)
        .filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,  # noqa: E712
            extract("year", ActualTransaction.transaction_date) == 2026,
            extract("month", ActualTransaction.transaction_date) <= 8,
        )
        .all()
    ):
        nome = (r.category or "").strip()
        sid = r.source_id or ""
        v = float(r.value or 0)
        code = cc_nome.get(r.cost_center_id, "")
        if sid.startswith("SP-MIG-"):
            sp_cat[nome] += v
            sp_cc[code] += v
            if "AFAC" in nome.upper():
                sp_afac += v
        elif sid.startswith("OUT-"):
            out_cat[nome] += v
            out_cc[code] += v
            if "AFAC" in nome.upper():
                out_afac += v

    print(f"{'categoria':44} {'SP':>14} {'OUT':>14} {'gap':>12}")
    for nome in CATEGORIAS:
        a, b = sp_cat.get(nome, 0.0), out_cat.get(nome, 0.0)
        print(f"{nome[:44]:44} {a:14,.2f} {b:14,.2f} {b - a:12,.2f}")
    print()
    for code in CCS:
        a, b = sp_cc.get(code, 0.0), out_cc.get(code, 0.0)
        print(f"{'CC ' + code:44} {a:14,.2f} {b:14,.2f} {b - a:12,.2f}")
    print(f"{'AFAC (todas as categorias)':44} {sp_afac:14,.2f} {out_afac:14,.2f} {out_afac - sp_afac:12,.2f}")

    # Total com a mesma regra do comparativo oficial (planos redutores)
    planos_id_by_name, planos_redutora = build_planos_maps(db)

    def total(pat: str, ate_agosto: bool) -> float:
        q = db.query(ActualTransaction).filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,  # noqa: E712
            ActualTransaction.source_id.like(pat),
            extract("year", ActualTransaction.transaction_date) == 2026,
        )
        if ate_agosto:
            q = q.filter(extract("month", ActualTransaction.transaction_date) <= 8)
        soma = 0.0
        for r in q.all():
            nome = (r.category or "").strip()
            v = float(r.value or 0)
            plano_id = planos_id_by_name.get(nome)
            soma += v if not plano_id else valor_despesa_sienge(v, plano_id, nome, planos_redutora)
        return soma

    print()
    for rotulo, ate_agosto in [("jan-ago", True), ("ano cheio", False)]:
        a, b = total("SP-MIG-%", ate_agosto), total("OUT-%", ate_agosto)
        print(f"{'TOTAL EMPRESA ' + rotulo:44} {a:14,.2f} {b:14,.2f} {b - a:12,.2f}")
    db.close()


if __name__ == "__main__":
    main()
