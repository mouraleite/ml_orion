"""Monta UserResponse com vários perfis e permissões unidas."""

from __future__ import annotations

from typing import Any

from app.core.access import merge_profile_permissions, profiles_for_user
from app.schemas.user import PerfilSimples, UserResponse


def attach_user_perfis(resp: UserResponse, user: Any) -> UserResponse:
    profiles = profiles_for_user(user)
    merged = merge_profile_permissions(profiles)
    simples: list[PerfilSimples] = []
    ids: list[int] = []
    for perfil in profiles:
        pid = getattr(perfil, "id", None)
        if pid is None:
            continue
        simples.append(PerfilSimples.model_validate(perfil))
        ids.append(int(pid))
    resp.perfis = simples
    resp.perfil_ids = ids
    if ids and resp.perfil_id is None:
        resp.perfil_id = ids[0]
    if simples:
        first = simples[0].model_copy()
        first.permissions = merged
        resp.perfil = first
    return resp
