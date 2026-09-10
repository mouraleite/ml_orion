"""Permissão Consolidação MLDU (Onda D)."""

from types import SimpleNamespace

from app.services.consolidacao_mldu_access import (
    MODULO_FORECAST,
    MODULO_ORCAMENTO,
    consolidacao_mldu_flags,
    pode_consolidacao_mldu,
)


def _user(role: str = "Usuario", perms: dict | None = None):
    perfil = SimpleNamespace(permissions=perms or {})
    return SimpleNamespace(role=role, perfil=perfil)


def test_filtro_aparece_para_qualquer_usuario_logado():
    u = _user(
        role="Consulta",
        perms={
            MODULO_ORCAMENTO: {"Consolidação MLDU": False},
            MODULO_FORECAST: {"Consolidação MLDU": False},
        },
    )
    assert pode_consolidacao_mldu(u, MODULO_ORCAMENTO) is True
    assert pode_consolidacao_mldu(u, MODULO_FORECAST) is True
    flags = consolidacao_mldu_flags(u)
    assert flags["pode_consolidacao_mldu_orcamento"] is True
    assert flags["pode_consolidacao_mldu_forecast"] is True


def test_sem_usuario_nao_libera():
    assert pode_consolidacao_mldu(None, MODULO_ORCAMENTO) is False
