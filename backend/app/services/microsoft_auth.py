"""Validação do id_token Microsoft Entra e vínculo ao colaborador ERP."""
from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

_jwks_clients: dict[str, PyJWKClient] = {}


def entra_configurado() -> bool:
    return bool((settings.AZURE_TENANT_ID or "").strip() and (settings.AZURE_CLIENT_ID or "").strip())


def _jwks_client(tenant: str) -> PyJWKClient:
    if tenant not in _jwks_clients:
        url = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
        _jwks_clients[tenant] = PyJWKClient(url, cache_keys=True)
    return _jwks_clients[tenant]


def validar_id_token_microsoft(id_token: str) -> dict[str, Any]:
    """Decodifica e valida id_token Entra (RS256 + JWKS)."""
    if not entra_configurado():
        raise HTTPException(
            status_code=503,
            detail="Login Microsoft não configurado (AZURE_TENANT_ID / AZURE_CLIENT_ID).",
        )
    tenant = settings.AZURE_TENANT_ID.strip()
    client_id = settings.AZURE_CLIENT_ID.strip()
    try:
        key = _jwks_client(tenant).get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=[
                f"https://login.microsoftonline.com/{tenant}/v2.0",
                f"https://sts.windows.net/{tenant}/",
            ],
            options={"require": ["exp", "iat", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token Microsoft inválido ou expirado.") from exc

    oid = (payload.get("oid") or payload.get("sub") or "").strip()
    if not oid:
        raise HTTPException(status_code=401, detail="Token Microsoft sem identificador (oid).")

    email = (
        payload.get("preferred_username")
        or payload.get("email")
        or payload.get("upn")
        or ""
    )
    email = str(email).strip().lower()
    return {
        "oid": oid,
        "email": email,
        "name": (payload.get("name") or "").strip() or None,
        "raw": payload,
    }


def resolver_usuario_microsoft(db: Session, *, oid: str, email: str) -> User:
    """Acha colaborador cadastrado por oid ou e-mail; liga o oid no primeiro login."""
    user = db.query(User).filter(User.microsoft_oid == oid).first()
    if user is None and email:
        user = (
            db.query(User)
            .filter(func.lower(User.email) == email.lower())
            .first()
        )
        if user is not None:
            if user.microsoft_oid and user.microsoft_oid != oid:
                raise HTTPException(
                    status_code=403,
                    detail="Este e-mail já está vinculado a outra conta Microsoft.",
                )
            user.microsoft_oid = oid
            db.add(user)
            db.commit()
            db.refresh(user)

    if user is None:
        raise HTTPException(
            status_code=403,
            detail="Usuário não cadastrado no ML Órion. Solicite acesso ao administrador.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")
    return user
