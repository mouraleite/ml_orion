"""Escopo de departamentos por usuário (Onda A — perfil + vínculos)."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.core.roles import is_admin_user, is_diretor_user
from app.models.departamento import Departamento


def can_see_all_departments(user: Any) -> bool:
    """Diretor/admin (e Desenvolvedor) enxergam todos os departamentos ativos."""
    if not user:
        return False
    if getattr(user, "full_name", None) == "Desenvolvedor":
        return True
    return is_admin_user(user) or is_diretor_user(user)


def departamentos_for_user(db: Session, user: Any) -> list[Departamento]:
    if can_see_all_departments(user):
        return (
            db.query(Departamento)
            .filter(Departamento.ativo == True)
            .order_by(Departamento.nome)
            .all()
        )
    linked = getattr(user, "departamentos", None) or []
    return sorted(linked, key=lambda d: (d.nome or "").lower())


def user_departamento_ids(user: Any, db: Session) -> list[int]:
    return [d.id for d in departamentos_for_user(db, user)]


def user_has_department_access(user: Any, db: Session, departamento_id: int) -> bool:
    if can_see_all_departments(user):
        exists = (
            db.query(Departamento.id)
            .filter(Departamento.id == departamento_id, Departamento.ativo == True)
            .first()
        )
        return exists is not None
    return departamento_id in user_departamento_ids(user, db)


def diretorias_for_user(db: Session, user: Any) -> list:
    """Diretorias cujo usuário enxerga todos os departamentos membros."""
    from sqlalchemy.orm import joinedload

    from app.models.departamento import Diretoria

    q = (
        db.query(Diretoria)
        .options(joinedload(Diretoria.departamentos))
        .filter(Diretoria.ativo == True)  # noqa: E712
        .order_by(Diretoria.nome)
    )
    if can_see_all_departments(user):
        return q.all()

    allowed = set(user_departamento_ids(user, db))
    out = []
    for di in q.all():
        membros = [d.id for d in (di.departamentos or []) if d.ativo]
        if membros and all(m in allowed for m in membros):
            out.append(di)
    return out


def first_departamento_nome(db: Session, departamento_ids: Sequence[int]) -> str | None:
    """Nome do primeiro departamento marcado — preenche o texto legado do colaborador."""
    ids = [int(i) for i in departamento_ids]
    if not ids:
        return None
    rows = (
        db.query(Departamento.id, Departamento.nome)
        .filter(Departamento.id.in_(ids))
        .all()
    )
    by_id = {int(row.id): row.nome for row in rows}
    for dept_id in ids:
        nome = by_id.get(dept_id)
        if nome:
            return nome
    return None


def sync_user_departamentos(db: Session, user_id: int, departamento_ids: Sequence[int]) -> None:
    from app.models.user import UserDepartamento

    db.query(UserDepartamento).filter(UserDepartamento.user_id == user_id).delete()
    for dept_id in departamento_ids:
        db.add(UserDepartamento(user_id=user_id, departamento_id=int(dept_id)))
