"""Transições de status (Orçamento e Forecast)."""

import pytest
from fastapi import HTTPException

from app.services.budget_status import exigir_permissao_status, resolver_transicao


def test_rascunho_envia_para_aprovacao():
    assert resolver_transicao("Rascunho", "Em aprovação") == ("Em aprovação", "enviar")


def test_reaberto_envia_para_aprovacao():
    assert resolver_transicao("Reaberto", "Em aprovação") == ("Em aprovação", "enviar")


def test_aprovar_grava_fechado():
    assert resolver_transicao("Em aprovação", "Fechado") == ("Fechado", "aprovar")


def test_pedido_aprovado_tambem_grava_fechado():
    assert resolver_transicao("Em aprovação", "Aprovado") == ("Fechado", "aprovar")


def test_rejeitar_volta_rascunho():
    assert resolver_transicao("Em aprovação", "Rascunho") == ("Rascunho", "rejeitar")


@pytest.mark.parametrize(
    "atual,pedido",
    [
        ("Rascunho", "Fechado"),
        ("Rascunho", "Aprovado"),
        ("Fechado", "Rascunho"),
        ("Aprovado", "Fechado"),
        ("Em aprovação", "Reaberto"),
    ],
)
def test_transicao_proibida(atual, pedido):
    with pytest.raises(HTTPException) as exc:
        resolver_transicao(atual, pedido)
    assert exc.value.status_code == 400


class _User:
    def __init__(self, **caps):
        self.perfil = None
        self.role = "Usuário Comum"
        self._caps = caps

    @property
    def capabilities_override(self):
        return self._caps


def test_analista_nao_aprova(monkeypatch):
    from app.core import access

    monkeypatch.setattr(
        access,
        "user_capabilities",
        lambda user: {"admin": False, "diretor": False, "gestor": False, "analista": True},
    )
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_status("aprovar", _User())
    assert exc.value.status_code == 403


def test_gestor_aprova(monkeypatch):
    from app.core import access

    monkeypatch.setattr(
        access,
        "user_capabilities",
        lambda user: {"admin": False, "diretor": False, "gestor": True, "analista": True},
    )
    exigir_permissao_status("aprovar", _User())
