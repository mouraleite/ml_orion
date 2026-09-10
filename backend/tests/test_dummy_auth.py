import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from app.api.deps import DEV_DUMMY_TOKEN, get_current_user
from app.core.config import settings


def test_dummy_token_liberado_em_development(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    user = get_current_user(db=db_session, token=DEV_DUMMY_TOKEN)
    assert user.email == "dev@mouraleite.com.br"
    assert user.role == "ADMIN"


def test_dummy_token_bloqueado_em_production(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    try:
        get_current_user(db=db_session, token=DEV_DUMMY_TOKEN)
        assert False, "deveria recusar dummy em production"
    except HTTPException as exc:
        assert exc.status_code == 403
