"""Resolução unificada: AccessProfile + papel legado (User.role)."""

from __future__ import annotations

from typing import Any

from app.core.roles import is_admin, is_analista, is_diretor, is_gestor, role_norm

CAPABILITIES_KEY = "_capabilities"
ROLE_KEY = "_role"
WRITE_KEY = "_write"

WRITE_DEFAULT_PROFILE_NAMES = {
    "administrador",
    "diretor",
    "controladoria",
    "gestor",
    "gestor financeiro",
    "marketing",
    "analista",
}

# Nomes de perfil gravados no SQLite → papel efetivo para autorização de API
PROFILE_NAME_TO_ROLE: dict[str, str] = {
    "administrador": "Administrador",
    "diretor": "Diretor",
    "controladoria": "Gestor",
    "gestor": "Gestor",
    "gestor financeiro": "Gestor",
    "marketing": "Analista",
    "analista": "Analista",
    "consulta": "Consulta",
    "visitante": "Visitante",
    "integracao": "Integracao",
    "integração": "Integracao",
}

_ROLE_RANK = {
    "Administrador": 50,
    "ADMIN": 50,
    "Desenvolvedor": 50,
    "Diretor": 40,
    "DIRETOR": 40,
    "Gestor": 30,
    "GESTOR": 30,
    "Analista": 20,
    "ANALISTA": 20,
}


def profiles_for_user(user: Any) -> list[Any]:
    extra = getattr(user, "perfis", None) or []
    if extra:
        return list(extra)
    one = getattr(user, "perfil", None)
    return [one] if one else []


def merge_profile_permissions(profiles: list[Any]) -> dict:
    """Une telas (OU) e criar/alterar se algum perfil liberar."""
    if not profiles:
        return {}
    raws: list[dict] = []
    names: list[str] = []
    for perfil in profiles:
        raw = getattr(perfil, "permissions", None)
        raws.append(raw if isinstance(raw, dict) else {})
        names.append(str(getattr(perfil, "name", "") or ""))

    modules: set[str] = set()
    for raw in raws:
        modules.update(str(k) for k in raw if not str(k).startswith("_"))

    out: dict[str, Any] = {}
    for mod in modules:
        buckets = [raw[mod] if isinstance(raw.get(mod), dict) else {} for raw in raws]
        keys: set[str] = set()
        for bucket in buckets:
            keys.update(bucket.keys())
        merged: dict[str, bool] = {}
        write_any = False
        for bucket, name in zip(buckets, names):
            if WRITE_KEY in bucket:
                write_any = write_any or bool(bucket[WRITE_KEY])
            else:
                write_any = write_any or (name.strip().lower() in WRITE_DEFAULT_PROFILE_NAMES)
        merged[WRITE_KEY] = write_any
        for key in keys:
            if str(key).startswith("_"):
                continue
            merged[key] = any(bool(bucket.get(key)) for bucket in buckets)
        out[mod] = merged

    caps = {"admin": False, "diretor": False, "gestor": False, "analista": False}
    has_caps = False
    for raw in raws:
        block = raw.get(CAPABILITIES_KEY)
        if isinstance(block, dict):
            has_caps = True
            for flag in caps:
                caps[flag] = caps[flag] or bool(block.get(flag))
    if has_caps:
        out[CAPABILITIES_KEY] = caps

    for raw in raws:
        explicit = raw.get(ROLE_KEY)
        if explicit:
            out[ROLE_KEY] = role_norm(str(explicit))
            break
    return out


def _profile_permissions(user: Any) -> dict:
    return merge_profile_permissions(profiles_for_user(user))


def _role_from_capabilities_block(caps: dict) -> str | None:
    if caps.get("admin"):
        return "Administrador"
    if caps.get("diretor"):
        return "Diretor"
    if caps.get("gestor"):
        return "Gestor"
    if caps.get("analista"):
        return "Analista"
    return None


def _rank_role(role: str) -> int:
    return _ROLE_RANK.get(role_norm(role), 0)


def effective_role(user: Any) -> str:
    """
    Papel usado na autorização da API.
    Ordem: permissions._role → permissions._capabilities → nomes dos perfis (o mais alto) → User.role
    """
    perms = _profile_permissions(user)

    explicit = perms.get(ROLE_KEY)
    if explicit:
        return role_norm(str(explicit)) or "Usuario"

    caps_block = perms.get(CAPABILITIES_KEY)
    if isinstance(caps_block, dict):
        from_caps = _role_from_capabilities_block(caps_block)
        if from_caps:
            return from_caps

    best = ""
    best_rank = -1
    for perfil in profiles_for_user(user):
        name = getattr(perfil, "name", None)
        if not name:
            continue
        mapped = PROFILE_NAME_TO_ROLE.get(str(name).strip().lower())
        if not mapped:
            continue
        rank = _rank_role(mapped)
        if rank > best_rank:
            best_rank = rank
            best = mapped
    if best:
        return best

    legacy = role_norm(getattr(user, "role", None))
    return legacy or "Usuario"


def user_capabilities(user: Any) -> dict[str, bool]:
    """Flags usadas por deps e expostas em /users/me."""
    perms = _profile_permissions(user)
    caps_block = perms.get(CAPABILITIES_KEY)
    if isinstance(caps_block, dict):
        return {
            "admin": bool(caps_block.get("admin")),
            "diretor": bool(caps_block.get("diretor")),
            "gestor": bool(caps_block.get("gestor")),
            "analista": bool(caps_block.get("analista")),
        }

    role = effective_role(user)
    return {
        "admin": is_admin(role),
        "diretor": is_diretor(role),
        "gestor": is_gestor(role),
        "analista": is_analista(role),
    }


def user_access_payload(user: Any) -> dict[str, Any]:
    return {
        "effective_role": effective_role(user),
        "capabilities": user_capabilities(user),
    }
