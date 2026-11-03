"""Primeiro mês de caixa do produto — só para o cadastro do terreno manual.

Não altera TIR, payback nem o mês em que o terreno entra no acompanhamento.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter


def yyyy_mm(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m")
    text = str(value).strip()
    if len(text) >= 7 and text[4] == "-":
        return text[:7]
    return None


def ids_centros_do_mesmo_produto(db: Session, cc: CostCenter) -> list[int]:
    from app.api.routes.tracking import _mesmo_produto_obra, parse_project_name

    _, produto = parse_project_name(cc)
    prefixo = (cc.id_sienge or "")[:3]
    consulta = db.query(CostCenter)
    if prefixo:
        consulta = consulta.filter(CostCenter.id_sienge.like(f"{prefixo}%"))
    ids: list[int] = []
    for membro in consulta.all():
        if membro.id == cc.id or _mesmo_produto_obra(produto, parse_project_name(membro)[1]):
            ids.append(membro.id)
    if cc.id not in ids:
        ids.append(cc.id)
    return ids


def primeiro_meses_caixa_produto(db: Session, cc: CostCenter) -> dict:
    ids = ids_centros_do_mesmo_produto(db, cc)
    caixa = yyyy_mm(
        db.query(func.min(ActualTransaction.transaction_date))
        .filter(
            ActualTransaction.cost_center_id.in_(ids),
            ActualTransaction.is_forecast.is_(False),
            ActualTransaction.transaction_type.in_(("INCOME", "OUTCOME")),
        )
        .scalar()
    )
    saida = yyyy_mm(
        db.query(func.min(ActualTransaction.transaction_date))
        .filter(
            ActualTransaction.cost_center_id.in_(ids),
            ActualTransaction.is_forecast.is_(False),
            ActualTransaction.transaction_type == "OUTCOME",
        )
        .scalar()
    )
    return {
        "primeiro_mes_caixa": caixa,
        "primeiro_mes_desembolso": saida,
        "mes_sugerido": caixa or saida,
    }
