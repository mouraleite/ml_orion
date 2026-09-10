"""Corporativo: residual (ex-Consolidado - Sienge).

Não altera filtro de orçado/realizado/DFC. Passo 4 consome classificar_planos_matriz.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.departamento import Departamento, DepartamentoPlano
from app.models.financial_plan import FinancialPlan
from app.models.forecast import Forecast
from app.models.orcamento import Orcamento

CORPORATIVO_NOME = "Corporativo"
_LEGADO_NORM = "consolidado - sienge"


def normalizar_nome_dept(nome: str | None) -> str:
    import unicodedata

    s = " ".join((nome or "").strip().split())
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.casefold()


def eh_corporativo(nome: str | None) -> bool:
    n = normalizar_nome_dept(nome)
    if n == "corporativo":
        return True
    if n == _LEGADO_NORM or n.replace(" ", "") == "consolidadosienge":
        return True
    return False


def _dept_is_residual(dept: Departamento) -> bool:
    if getattr(dept, "is_residual", False):
        return True
    return eh_corporativo(dept.nome)


def corporativo_id(db: Session) -> Optional[int]:
    dept = (
        db.query(Departamento)
        .filter(Departamento.is_residual == True)  # noqa: E712
        .first()
    )
    if dept:
        return dept.id
    for d in db.query(Departamento).all():
        if eh_corporativo(d.nome):
            return d.id
    return None


def corporativo_id_or_neg(db: Session) -> int:
    cid = corporativo_id(db)
    return cid if cid is not None else -1


def ensure_corporativo_departamento(db: Session) -> Departamento:
    """Garante um departamento residual chamado Corporativo (renomeia o legado)."""
    dept = (
        db.query(Departamento)
        .filter(Departamento.is_residual == True)  # noqa: E712
        .first()
    )
    if dept is None:
        for d in db.query(Departamento).all():
            if eh_corporativo(d.nome):
                dept = d
                break
    if dept is None:
        dept = Departamento(nome=CORPORATIVO_NOME, ativo=True, is_residual=True)
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    changed = False
    if dept.nome != CORPORATIVO_NOME:
        dept.nome = CORPORATIVO_NOME
        changed = True
    if not dept.is_residual:
        dept.is_residual = True
        changed = True
    if not dept.ativo:
        dept.ativo = True
        changed = True
    if changed:
        db.commit()
        db.refresh(dept)
    return dept


def classificar_planos_matriz(db: Session) -> dict[int, str]:
    """exclusivo = 1 dept; comum = 2+; residual = nenhum (Corporativo não conta)."""
    residual_ids = {d.id for d in db.query(Departamento).all() if _dept_is_residual(d)}
    cobertura: dict[int, set[int]] = defaultdict(set)
    links = (
        db.query(DepartamentoPlano)
        .filter(DepartamentoPlano.permitido == True)  # noqa: E712
        .all()
    )
    for lk in links:
        if lk.departamento_id in residual_ids:
            continue
        if lk.plano_financeiro_id is None:
            continue
        cobertura[lk.plano_financeiro_id].add(lk.departamento_id)

    out: dict[int, str] = {}
    for p in db.query(FinancialPlan.id).all():
        pid = p[0]
        n = len(cobertura.get(pid, ()))
        if n == 0:
            out[pid] = "residual"
        elif n == 1:
            out[pid] = "exclusivo"
        else:
            out[pid] = "comum"
    return out


def resumo_residual(db: Session) -> dict[str, Any]:
    dept = ensure_corporativo_departamento(db)
    classes = classificar_planos_matriz(db)
    orcs_sem = (
        db.query(Orcamento)
        .filter(Orcamento.departamento_id.is_(None), Orcamento.status != "Substituído")
        .count()
    )
    fcs_sem = (
        db.query(Forecast)
        .filter(Forecast.departamento_id.is_(None), Forecast.status != "Substituído")
        .count()
    )
    return {
        "departamento_id": dept.id,
        "nome": dept.nome,
        "planos_residuais": sum(1 for v in classes.values() if v == "residual"),
        "planos_comuns": sum(1 for v in classes.values() if v == "comum"),
        "planos_exclusivos": sum(1 for v in classes.values() if v == "exclusivo"),
        "orcamentos_sem_departamento": orcs_sem,
        "forecasts_sem_departamento": fcs_sem,
    }
