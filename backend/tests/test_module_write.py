"""Criar/alterar por módulo."""

from types import SimpleNamespace

from app.core.module_write import (
    can_write_module,
    default_module_write,
    module_for_path,
    should_skip_write_check,
    write_modules_payload,
)


def _user(role: str = "READ_ONLY", perfil_name: str | None = None, perms: dict | None = None):
    perfil = None
    if perfil_name is not None:
        perfil = SimpleNamespace(name=perfil_name, permissions=perms or {})
    return SimpleNamespace(role=role, perfil=perfil)


def test_diretor_sem_flag_pode_alterar():
    u = _user(role="Usuario", perfil_name="Diretor")
    assert can_write_module(u, "Orçamento") is True
    assert write_modules_payload(u)["Rentabilidade de Produtos"] is True


def test_engenharia_sem_flag_so_ve():
    u = _user(perfil_name="Engenharia")
    assert default_module_write("Engenharia") is False
    assert can_write_module(u, "Orçamento") is False
    assert can_write_module(u, "Rentabilidade de Produtos") is False


def test_flag_explicita_vence_nome_do_perfil():
    u = _user(
        role="Usuario",
        perfil_name="Diretor",
        perms={"Orçamento": {"_write": False, "Orçamento de Despesas": True}},
    )
    assert can_write_module(u, "Orçamento") is False
    u2 = _user(
        role="Usuario",
        perfil_name="Engenharia",
        perms={"Orçamento": {"_write": True}},
    )
    assert can_write_module(u2, "Orçamento") is True
    assert can_write_module(u2, "Forecast") is False


def test_mesmo_perfil_um_so_ve_outro_altera():
    perms = {"Orçamento": {"_write": True, "Orçamento de Despesas": True}}
    vendedor = _user(role="READ_ONLY", perfil_name="Engenharia", perms=perms)
    gerente = _user(role="Usuario", perfil_name="Engenharia", perms=perms)
    assert can_write_module(vendedor, "Orçamento") is False
    assert can_write_module(gerente, "Orçamento") is True


def test_admin_sempre_altera():
    u = _user(role="ADMIN", perfil_name="Engenharia", perms={"Orçamento": {"_write": False}})
    assert can_write_module(u, "Orçamento") is True


def test_somente_visualizacao_vence_perfil_administrador():
    u = _user(role="READ_ONLY", perfil_name="Administrador")
    assert can_write_module(u, "Orçamento") is False


def test_varios_perfis_write_se_algum_liberar():
    tesouraria = SimpleNamespace(
        name="Tesouraria",
        permissions={"Orçamento": {"Orçamento de Despesas": True, "_write": True}},
    )
    engenharia = SimpleNamespace(
        name="Engenharia",
        permissions={"Orçamento": {"Orçamento de Despesas": True, "_write": False}},
    )
    u = SimpleNamespace(role="Usuario", perfil=tesouraria, perfis=[tesouraria, engenharia])
    assert can_write_module(u, "Orçamento") is True
    bloqueado = SimpleNamespace(role="READ_ONLY", perfil=tesouraria, perfis=[tesouraria, engenharia])
    assert can_write_module(bloqueado, "Orçamento") is False


def test_mapeia_path_mutante():
    assert module_for_path("/api/v1/orcamentos/despesas/2026/salvar") == "Orçamento"
    assert module_for_path("/api/v1/viabilities/1") == "Rentabilidade de Produtos"
    assert module_for_path("/api/v1/apoio/empresas") == "Apoio"
    assert should_skip_write_check("GET", "/api/v1/orcamentos/x") is True
    assert should_skip_write_check("POST", "/api/v1/orcamentos/criar") is False
    assert should_skip_write_check("POST", "/api/v1/login/access-token") is True
