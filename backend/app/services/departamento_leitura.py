"""Escopo de leitura Orçamento/Forecast por departamento (passo 4).

Não altera fórmula, arredondamento nem persistência de valores.
Corporativo e Todos: total da empresa. Departamento operacional: só a matriz.
Diretoria: soma sem interseção dos departamentos membros.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import false, or_, true
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.services.corporativo import corporativo_id, eh_corporativo

DEPARTAMENTO_TODOS_ID = 0
TODOS_NOME = "Todos os departamentos"
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def eh_todos(dept: Any) -> bool:
    return getattr(dept, "id", None) == DEPARTAMENTO_TODOS_ID


def eh_diretoria(dept: Any) -> bool:
    did = getattr(dept, "id", None)
    return isinstance(did, int) and did < 0


def diretoria_db_id(dept: Any) -> Optional[int]:
    if not eh_diretoria(dept):
        return None
    explicit = getattr(dept, "diretoria_db_id", None)
    if explicit is not None:
        return int(explicit)
    return -int(dept.id)


def departamento_sentinela_todos() -> Departamento:
    return Departamento(
        id=DEPARTAMENTO_TODOS_ID,
        nome=TODOS_NOME,
        ativo=True,
        is_residual=False,
    )


def departamento_sentinela_diretoria(db: Session, diretoria_id: int) -> Departamento:
    from app.models.departamento import Diretoria

    di = db.query(Diretoria).filter(Diretoria.id == diretoria_id).first()
    nome = di.nome if di else f"Diretoria {diretoria_id}"
    sent = Departamento(
        id=-int(diretoria_id),
        nome=f"Diretoria: {nome}",
        ativo=True,
        is_residual=False,
    )
    sent.diretoria_db_id = int(diretoria_id)  # type: ignore[attr-defined]
    return sent


def membros_ids_diretoria(db: Session, dept: Any) -> list[int]:
    did = diretoria_db_id(dept)
    if did is None:
        return []
    rows = (
        db.query(Departamento.id)
        .filter(
            Departamento.diretoria_id == did,
            Departamento.ativo == True,  # noqa: E712
        )
        .all()
    )
    return [r[0] for r in rows]


def eh_residual_leitura(dept: Any) -> bool:
    if dept is None or eh_todos(dept) or eh_diretoria(dept):
        return False
    if getattr(dept, "is_residual", False):
        return True
    return eh_corporativo(getattr(dept, "nome", None))


def criterio_departamento(coluna, db: Session, dept: Any):
    """Filtro SQL de documentos (orçamento/forecast) no departamento ativo."""
    if eh_todos(dept):
        return true()
    if eh_diretoria(dept):
        ids = list(membros_ids_diretoria(db, dept))
        # Carga histórica pode estar só no residual; escolher_documentos decide o fallback.
        cid = corporativo_id(db)
        if cid is not None and cid not in ids:
            ids.append(cid)
        if not ids:
            return false()
        return coluna.in_(ids)
    if eh_residual_leitura(dept):
        return or_(coluna == dept.id, coluna.is_(None))
    return coluna == dept.id


def criterio_departamento_id(coluna, db: Session, dept_id: int):
    if dept_id == DEPARTAMENTO_TODOS_ID:
        return true()
    if dept_id < 0:
        return criterio_departamento(
            coluna, db, departamento_sentinela_diretoria(db, -dept_id)
        )
    dept = db.query(Departamento).filter(Departamento.id == dept_id).first()
    if dept is None:
        return coluna == dept_id
    return criterio_departamento(coluna, db, dept)


def departamento_id_realizado(db: Session, authorization_name: str | None) -> Optional[int]:
    """De-para / nome Apoio → departamento; sem name ou sem cadastro → Corporativo."""
    from app.models.departamento import DeparaAutorizacaoDepartamento
    from app.services.depara_autorizacao import normalizar_nome, sugerir_departamento_id

    cid = corporativo_id(db)
    nome = (authorization_name or "").strip()
    if not nome:
        return cid

    alvo = normalizar_nome(nome)
    row = None
    for cand in db.query(DeparaAutorizacaoDepartamento).all():
        if normalizar_nome(cand.nome_sienge) == alvo:
            row = cand
            break
    if row is not None:
        return row.departamento_id if row.departamento_id is not None else cid

    depts = db.query(Departamento).all()
    sug = sugerir_departamento_id(nome, depts)
    return sug if sug is not None else cid


def nomes_autorizacao_do_departamento(db: Session, dept: Any) -> list[str]:
    """Nomes Sienge / Apoio que caem neste departamento (ou nos membros da diretoria)."""
    from app.models.departamento import DeparaAutorizacaoDepartamento

    nomes: list[str] = []
    visto: set[str] = set()

    def _add(raw: str | None) -> None:
        nome = (raw or "").strip()
        if not nome:
            return
        key = nome.casefold()
        if key in visto:
            return
        visto.add(key)
        nomes.append(nome)

    if eh_diretoria(dept):
        for mid in membros_ids_diretoria(db, dept):
            m = db.query(Departamento).filter(Departamento.id == mid).first()
            if m is None:
                continue
            _add(m.nome)
            for row in (
                db.query(DeparaAutorizacaoDepartamento)
                .filter(DeparaAutorizacaoDepartamento.departamento_id == mid)
                .all()
            ):
                _add(row.nome_sienge)
        return nomes

    _add(getattr(dept, "nome", None))
    did = getattr(dept, "id", None)
    if did is not None and did > 0:
        for row in (
            db.query(DeparaAutorizacaoDepartamento)
            .filter(DeparaAutorizacaoDepartamento.departamento_id == did)
            .all()
        ):
            _add(row.nome_sienge)
    return nomes


def parcela_pertence_ao_dept(db: Session, authorization_name: str | None, dept: Any) -> bool:
    """Todos e Corporativo: realizado da empresa. Diretoria: membros. Demais: de-para."""
    if eh_todos(dept) or eh_residual_leitura(dept):
        return True
    alvo = departamento_id_realizado(db, authorization_name)
    if eh_diretoria(dept):
        return alvo is not None and alvo in set(membros_ids_diretoria(db, dept))
    return alvo is not None and alvo == getattr(dept, "id", None)


def _planos_por_tp(db: Session, tp_conta: str | None, ids: Optional[list[int]] = None):
    from app.models.financial_plan import FinancialPlan

    q = db.query(FinancialPlan)
    if ids is not None:
        if not ids:
            return []
        q = q.filter(FinancialPlan.id.in_(ids))
    if tp_conta == "D":
        q = q.filter(FinancialPlan.tp_conta == "R", FinancialPlan.db_id.like("2%"))
    elif tp_conta == "R":
        q = q.filter(FinancialPlan.tp_conta == "R", FinancialPlan.db_id.like("1%"))
    else:
        q = q.filter(FinancialPlan.tp_conta == "R")
    return q.all()


def planos_ids_leitura(db: Session, dept: Any, tp_conta: str | None = None) -> list[int]:
    """Catálogo de planos. Corporativo/Todos = empresa. Diretoria = união das matrizes."""
    from app.models.departamento import DepartamentoPlano

    if eh_todos(dept) or eh_residual_leitura(dept):
        return [p.id for p in _planos_por_tp(db, tp_conta)]

    if eh_diretoria(dept):
        membros = membros_ids_diretoria(db, dept)
        if not membros:
            return []
        planos_dept = (
            db.query(DepartamentoPlano.plano_financeiro_id)
            .filter(
                DepartamentoPlano.departamento_id.in_(membros),
                DepartamentoPlano.permitido == True,  # noqa: E712
            )
            .distinct()
            .all()
        )
        planos_ids = [p[0] for p in planos_dept]
        if not planos_ids:
            return []
        return [p.id for p in _planos_por_tp(db, tp_conta, planos_ids)]

    planos_dept = (
        db.query(DepartamentoPlano.plano_financeiro_id)
        .filter(
            DepartamentoPlano.departamento_id == dept.id,
            DepartamentoPlano.permitido == True,  # noqa: E712
        )
        .all()
    )
    planos_ids = [p[0] for p in planos_dept]
    if not planos_ids:
        return []
    return [p.id for p in _planos_por_tp(db, tp_conta, planos_ids)]


def produtos_ids_leitura(db: Session, dept: Any) -> list[int]:
    """Leitura usa todos os centros ativos — a junção produto×plano não alimenta os totais validados."""
    from app.models.cost_center import CostCenter

    _ = dept
    return [p.id for p in db.query(CostCenter).filter(CostCenter.status == "Ativo").all()]


def escolher_documentos_leitura(query, model, dept) -> list:
    """Documento vigente: um por departamento. Em Todos/Diretoria, um por dept membro."""
    statuses = ("Aprovado", "Fechado")

    def pick(q):
        o = q.filter(model.status.in_(statuses)).order_by(model.id.desc()).first()
        if o is None:
            o = q.order_by(model.id.desc()).first()
        return o

    if eh_diretoria(dept):
        db = query.session
        ids = membros_ids_diretoria(db, dept)
        out = []
        seen: set[int] = set()
        for did in ids:
            o = pick(query.filter(model.departamento_id == did))
            if o is not None and o.id not in seen:
                seen.add(o.id)
                out.append(o)
        # Sem documento nos membros: lê Corporativo; itens ficam limitados à união
        # dos planos dos membros (planos_ids_leitura) — não altera Todos/Corporativo.
        if not out:
            cid = corporativo_id(db)
            if cid is not None:
                o = pick(query.filter(model.departamento_id == cid))
                if o is not None:
                    out.append(o)
        return out

    if not eh_todos(dept):
        o = pick(query)
        return [o] if o else []

    ids = [row[0] for row in query.with_entities(model.departamento_id).distinct().all()]
    out = []
    seen: set[int] = set()
    for did in ids:
        q = (
            query.filter(model.departamento_id.is_(None))
            if did is None
            else query.filter(model.departamento_id == did)
        )
        o = pick(q)
        if o is not None and o.id not in seen:
            seen.add(o.id)
            out.append(o)
    return out


def rejeitar_gravacao_todos(dept: Any, method: str | None) -> None:
    rejeitar_gravacao_contexto(dept, method)


def rejeitar_gravacao_contexto(dept: Any, method: str | None) -> None:
    from fastapi import HTTPException, status

    if (eh_todos(dept) or eh_diretoria(dept)) and (method or "").upper() in _WRITE_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione um departamento para lançar.",
        )
