"""Criar/alterar por módulo (perfil), independente de abrir a tela."""

from __future__ import annotations

from typing import Any

from app.core.access import _profile_permissions, profiles_for_user, user_capabilities
from app.core.roles import is_admin, is_user_view_only

WRITE_KEY = "_write"

MODULE_TITLES = (
    "Rentabilidade de Produtos",
    "Modelagem Financeira",
    "Orçamento",
    "Forecast",
    "Consolidação",
    "Governança e Índices",
    "Apoio",
    "Segurança",
)

WRITE_DEFAULT_PROFILE_NAMES = {
    "administrador",
    "diretor",
    "controladoria",
    "gestor",
    "gestor financeiro",
    "marketing",
    "analista",
}

# Prefixos mais longos primeiro.
PATH_PREFIX_TO_MODULE: tuple[tuple[str, str], ...] = (
    ("/api/v1/matriz-permissoes", "Apoio"),
    ("/api/v1/perfis-acesso", "Segurança"),
    ("/api/v1/market-indices", "Apoio"),
    ("/api/v1/acompanhamento", "Orçamento"),
    ("/api/v1/viabilities", "Rentabilidade de Produtos"),
    ("/api/v1/partnership", "Apoio"),
    ("/api/v1/integracao", "Apoio"),
    ("/api/v1/migration", "Apoio"),
    ("/api/v1/auditoria", "Segurança"),
    ("/api/v1/governance", "Governança e Índices"),
    ("/api/v1/orcamentos", "Orçamento"),
    ("/api/v1/fechamento", "Orçamento"),
    ("/api/v1/forecasts", "Forecast"),
    ("/api/v1/tracking", "Rentabilidade de Produtos"),
    ("/api/v1/analysis", "Rentabilidade de Produtos"),
    ("/api/v1/dashboard", "Orçamento"),
    ("/api/v1/holding", "Consolidação"),
    ("/api/v1/curves", "Apoio"),
    ("/api/v1/sienge", "Apoio"),
    ("/api/v1/users", "Segurança"),
    ("/api/v1/apoio", "Apoio"),
    ("/api/v1/sync", "Apoio"),
)

SKIP_PREFIXES = (
    "/api/v1/login",
    "/api/v1/system",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
)

WRITE_BLOCK_DETAIL = "Você não pode criar nem alterar neste módulo."


def _profile_name(user: Any) -> str:
    for perfil in profiles_for_user(user):
        name = getattr(perfil, "name", None)
        if name:
            return str(name).strip().lower()
    return ""


def _any_profile_write_default(user: Any) -> bool:
    for perfil in profiles_for_user(user):
        name = str(getattr(perfil, "name", "") or "").strip().lower()
        if name in WRITE_DEFAULT_PROFILE_NAMES:
            return True
    return False


def default_module_write(profile_name: str | None) -> bool:
    return (profile_name or "").strip().lower() in WRITE_DEFAULT_PROFILE_NAMES


def can_write_module(user: Any, module_title: str) -> bool:
    if user is None:
        return False
    if is_admin(getattr(user, "role", None)):
        return True
    if is_user_view_only(user):
        return False
    caps = user_capabilities(user)
    if caps.get("admin"):
        return True
    perms = _profile_permissions(user)
    bucket = perms.get(module_title)
    if isinstance(bucket, dict) and WRITE_KEY in bucket:
        return bool(bucket[WRITE_KEY])
    return _any_profile_write_default(user)


def write_modules_payload(user: Any) -> dict[str, bool]:
    return {title: can_write_module(user, title) for title in MODULE_TITLES}


def module_for_path(path: str) -> str | None:
    for prefix, module in PATH_PREFIX_TO_MODULE:
        if path == prefix or path.startswith(prefix + "/"):
            return module
    return None


def should_skip_write_check(method: str, path: str) -> bool:
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return True
    if path in {"/", "/health"}:
        return True
    return any(path == p or path.startswith(p + "/") or path.startswith(p) for p in SKIP_PREFIXES)
