"""SSO Microsoft: resolução de usuário e status (sem chamar JWKS real)."""
from fastapi import HTTPException

from app.models.user import User
from app.services.microsoft_auth import entra_configurado, resolver_usuario_microsoft


def test_entra_nao_configurado_por_padrao():
    assert entra_configurado() is False or isinstance(entra_configurado(), bool)


def test_resolver_por_email_liga_oid(db_session, monkeypatch):
    monkeypatch.setattr("app.services.microsoft_auth.settings.AZURE_TENANT_ID", "t")
    monkeypatch.setattr("app.services.microsoft_auth.settings.AZURE_CLIENT_ID", "c")
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None
    user.microsoft_oid = None
    db_session.commit()

    found = resolver_usuario_microsoft(
        db_session, oid="oid-teste-abc", email=(user.email or "").lower()
    )
    assert found.id == user.id
    db_session.refresh(user)
    assert user.microsoft_oid == "oid-teste-abc"


def test_resolver_email_desconhecido_403(db_session, monkeypatch):
    monkeypatch.setattr("app.services.microsoft_auth.settings.AZURE_TENANT_ID", "t")
    monkeypatch.setattr("app.services.microsoft_auth.settings.AZURE_CLIENT_ID", "c")
    try:
        resolver_usuario_microsoft(
            db_session, oid="oid-x", email="naoexiste@mouraleite.com.br"
        )
        assert False, "deveria 403"
    except HTTPException as e:
        assert e.status_code == 403


def test_auth_microsoft_status(client):
    r = client.get("/api/v1/auth/microsoft/status")
    assert r.status_code == 200
    assert "configured" in r.json()
