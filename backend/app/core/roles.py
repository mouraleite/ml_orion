"""Aliases de papel. O banco grava 'Administrador'/'Gestor'; várias rotas checavam só 'ADMIN'/'GESTOR'."""


def role_norm(role: str | None) -> str:
    return (role or "").strip()


def is_admin(role: str | None) -> bool:
    return role_norm(role) in {"ADMIN", "Administrador", "Desenvolvedor"}


def is_diretor(role: str | None) -> bool:
    return is_admin(role) or role_norm(role) in {"DIRETOR", "Diretor"}


def is_gestor(role: str | None) -> bool:
    return is_diretor(role) or role_norm(role) in {"GESTOR", "Gestor"}


def is_analista(role: str | None) -> bool:
    return is_gestor(role) or role_norm(role) in {"ANALISTA", "Analista"}


VIEW_ONLY_ROLES = {"READ_ONLY", "VISITANTE", "Consulta"}


def is_user_view_only(user) -> bool:
    """Papel do colaborador (não o nome do perfil): só vê, mesmo com o mesmo perfil de outro que altera."""
    if user is None:
        return True
    if is_admin(getattr(user, "role", None)):
        return False
    return role_norm(getattr(user, "role", None)) in VIEW_ONLY_ROLES


def is_admin_user(user) -> bool:
    from app.core.access import user_capabilities
    return user_capabilities(user)["admin"]


def is_diretor_user(user) -> bool:
    from app.core.access import user_capabilities
    return user_capabilities(user)["diretor"]


def is_gestor_user(user) -> bool:
    from app.core.access import user_capabilities
    return user_capabilities(user)["gestor"]


def is_analista_user(user) -> bool:
    from app.core.access import user_capabilities
    return user_capabilities(user)["analista"]
