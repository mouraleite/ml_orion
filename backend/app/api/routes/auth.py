from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.core import security
from app.core.access import user_access_payload
from app.core.module_write import write_modules_payload
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token, UserResponse, UserCapabilities, DepartamentoSimples, DiretoriaSimples
from app.services.user_department_scope import can_see_all_departments, departamentos_for_user, diretorias_for_user
from app.services.consolidacao_mldu_access import consolidacao_mldu_flags
from app.services.user_response import attach_user_perfis
from app.services.microsoft_auth import (
    entra_configurado,
    resolver_usuario_microsoft,
    validar_id_token_microsoft,
)

router = APIRouter()


class MicrosoftLoginBody(BaseModel):
    id_token: str = Field(..., min_length=20)


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, pega form_data.username (usado como email) e senha
    """
    user = (
        db.query(User)
        .filter(func.lower(User.email) == (form_data.username or "").strip().lower())
        .first()
    )
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/auth/microsoft", response_model=Token)
def login_microsoft(body: MicrosoftLoginBody, db: Session = Depends(deps.get_db)) -> Any:
    """Troca id_token Entra pelo JWT interno do ERP (colaborador já cadastrado)."""
    claims = validar_id_token_microsoft(body.id_token)
    user = resolver_usuario_microsoft(db, oid=claims["oid"], email=claims["email"])
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/auth/microsoft/status")
def microsoft_auth_status() -> Any:
    """Frontend usa para saber se o botão Microsoft deve autenticar de verdade."""
    return {"configured": entra_configurado()}


def _serialize_user_me(db: Session, current_user: User) -> UserResponse:
    user = current_user
    if getattr(current_user, "id", None):
        loaded = (
            db.query(User)
            .options(joinedload(User.perfil), joinedload(User.perfis), joinedload(User.departamentos))
            .filter(User.id == current_user.id)
            .first()
        )
        if loaded:
            user = loaded
    access = user_access_payload(user)
    resp = UserResponse.model_validate(user)
    resp.effective_role = access["effective_role"]
    resp.capabilities = UserCapabilities(**access["capabilities"])
    resp.pode_ver_todos_departamentos = can_see_all_departments(user)
    holding_flags = consolidacao_mldu_flags(user)
    resp.pode_consolidacao_mldu_orcamento = holding_flags["pode_consolidacao_mldu_orcamento"]
    resp.pode_consolidacao_mldu_forecast = holding_flags["pode_consolidacao_mldu_forecast"]
    resp.write_modules = write_modules_payload(user)
    depts = departamentos_for_user(db, user)
    resp.departamentos = [DepartamentoSimples.model_validate(d) for d in depts]
    resp.diretorias = [
        DiretoriaSimples(
            id=di.id,
            nome=di.nome,
            departamento_ids=[d.id for d in (di.departamentos or []) if d.ativo],
        )
        for di in diretorias_for_user(db, user)
    ]
    return attach_user_perfis(resp, user)


@router.get("/users/me", response_model=UserResponse)
def read_user_me(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Usuário atual com papel efetivo (perfil + legado)."""
    return _serialize_user_me(db, current_user)
