"""Vínculos de um colaborador com vários perfis de acesso."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.models.user import User, UserPerfil


def sync_user_perfis(db: Session, user_id: int, perfil_ids: Sequence[int]) -> None:
    db.query(UserPerfil).filter(UserPerfil.user_id == user_id).delete()
    seen: set[int] = set()
    ordered: list[int] = []
    for raw in perfil_ids:
        pid = int(raw)
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        db.add(UserPerfil(user_id=user_id, perfil_id=pid))
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        user.perfil_id = ordered[0] if ordered else None
