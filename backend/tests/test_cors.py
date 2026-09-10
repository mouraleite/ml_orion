import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core import config
from app.core.config import cors_allow_origins


def test_cors_development_aceita_asterisco(monkeypatch):
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(config.settings, "CORS_ORIGINS", "*")
    assert cors_allow_origins() == ["*"]


def test_cors_production_nao_deixa_asterisco(monkeypatch):
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config.settings, "CORS_ORIGINS", "*")
    assert "http://localhost:3000" in cors_allow_origins()
    assert "*" not in cors_allow_origins()
