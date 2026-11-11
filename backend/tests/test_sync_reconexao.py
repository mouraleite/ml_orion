"""Sync repete o CC uma vez quando a conexão com o banco cai (11/11/2026)."""
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from app.services import sienge_sync


class _DbFalso:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


def _queda():
    return OperationalError("SELECT 1", {}, Exception("SSL connection has been closed unexpectedly"))


def test_repete_cc_quando_conexao_cai(monkeypatch):
    chamadas = []

    def falso(db, cc, ini, fim, include_engineering=False):
        chamadas.append(cc.id_sienge)
        if len(chamadas) == 1:
            raise _queda()

    monkeypatch.setattr(sienge_sync, "sync_single_cc_sienge_data", falso)
    db = _DbFalso()
    sienge_sync._sync_cc_com_reconexao(db, SimpleNamespace(id_sienge="10100"), "2026-09-01", "2026-11-11")
    assert chamadas == ["10100", "10100"]
    assert db.rollbacks == 1


def test_segunda_queda_propaga(monkeypatch):
    def falso(db, cc, ini, fim, include_engineering=False):
        raise _queda()

    monkeypatch.setattr(sienge_sync, "sync_single_cc_sienge_data", falso)
    with pytest.raises(OperationalError):
        sienge_sync._sync_cc_com_reconexao(_DbFalso(), SimpleNamespace(id_sienge="1"), "a", "b")


def test_outro_erro_nao_repete(monkeypatch):
    chamadas = []

    def falso(db, cc, ini, fim, include_engineering=False):
        chamadas.append(1)
        raise ValueError("dado ruim")

    monkeypatch.setattr(sienge_sync, "sync_single_cc_sienge_data", falso)
    with pytest.raises(ValueError):
        sienge_sync._sync_cc_com_reconexao(_DbFalso(), SimpleNamespace(id_sienge="1"), "a", "b")
    assert chamadas == [1]
