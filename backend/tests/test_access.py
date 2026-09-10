import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from app.core.access import effective_role, user_capabilities
from app.core.roles import is_admin_user, is_diretor_user, is_gestor_user


def _user(role: str = "Usuario", perfil_name: str | None = None, perms: dict | None = None):
    perfil = None
    if perfil_name is not None:
        perfil = SimpleNamespace(name=perfil_name, permissions=perms or {})
    return SimpleNamespace(role=role, perfil=perfil)


def test_perfil_diretor_sobrescreve_role_legado():
    u = _user(role="READ_ONLY", perfil_name="Diretor")
    assert effective_role(u) == "Diretor"
    assert is_diretor_user(u)
    assert not is_admin_user(u)


def test_perfil_administrador_concede_admin():
    u = _user(role="Usuario", perfil_name="Administrador")
    caps = user_capabilities(u)
    assert caps["admin"] is True
    assert is_admin_user(u)


def test_capabilities_explicitas_no_json():
    u = _user(
        role="Consulta",
        perfil_name="Custom",
        perms={"_capabilities": {"gestor": True, "admin": False, "diretor": False, "analista": True}},
    )
    assert effective_role(u) == "Gestor"
    assert is_gestor_user(u)
    assert not is_admin_user(u)


def test_sem_perfil_usa_role_legado():
    u = _user(role="Gestor")
    assert effective_role(u) == "Gestor"
    assert is_gestor_user(u)


def test_varios_perfis_une_telas_e_write():
    from app.core.access import _profile_permissions

    tesouraria = SimpleNamespace(
        id=1,
        name="Tesouraria",
        permissions={"Orçamento": {"Orçamento de Despesas": True, "_write": True}},
    )
    engenharia = SimpleNamespace(
        id=2,
        name="Engenharia",
        permissions={"Rentabilidade de Produtos": {"Viabilidades": True, "_write": False}},
    )
    u = SimpleNamespace(role="Usuario", perfil=tesouraria, perfis=[tesouraria, engenharia])
    perms = _profile_permissions(u)
    assert perms["Orçamento"]["Orçamento de Despesas"] is True
    assert perms["Rentabilidade de Produtos"]["Viabilidades"] is True
    assert perms["Orçamento"]["_write"] is True
    assert perms["Rentabilidade de Produtos"]["_write"] is False


def test_varios_perfis_papel_mais_alto():
    analista = SimpleNamespace(id=1, name="Analista", permissions={})
    diretor = SimpleNamespace(id=2, name="Diretor", permissions={})
    u = SimpleNamespace(role="Usuario", perfil=analista, perfis=[analista, diretor])
    assert effective_role(u) == "Diretor"
