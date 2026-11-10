"""Rotas antigas desativadas em 10/11/2026 (cota REST do Sienge e protótipo quebrado)."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.api import deps
from app.models.user import User


@pytest.fixture
def client():
    u = User(id=7, email="a@test.com", full_name="A", role="Administrador", hashed_password="x")
    u.is_active = True
    app.dependency_overrides[deps.get_current_user] = lambda: u
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_sync_antigo_do_sienge_desativado(client, monkeypatch):
    import app.api.routes.sienge as rota
    monkeypatch.setattr(rota, "ErpIntegrationService", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não pode chamar o Sienge")))
    r = client.post("/api/v1/sienge/sync")
    assert r.status_code == 410


def test_sync_de_actuals_da_viabilidade_desativado(client):
    r = client.post("/api/v1/viabilities/phases/1/actuals/sync")
    assert r.status_code == 410
