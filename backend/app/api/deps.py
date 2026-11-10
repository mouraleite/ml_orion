from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.core.access import effective_role
from app.core.roles import is_admin_user, is_diretor_user, is_analista_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload
from app.services.user_department_scope import can_see_all_departments, user_has_department_access
from app.db.audit_listener import current_user_id

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

DEV_DUMMY_TOKEN = "dummy-token-for-dev"


def _dev_dummy_auth_allowed() -> bool:
    return settings.ENVIRONMENT.strip().lower() not in ("production", "prod")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
):
    if token == DEV_DUMMY_TOKEN:
        if not _dev_dummy_auth_allowed():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Atalho de desenvolvimento desativado neste ambiente.",
            )
        class MockUser:
            id = 9999
            email = "dev@mouraleite.com.br"
            full_name = "Desenvolvedor"
            role = "ADMIN"
            is_active = True
            departamentos = []
        current_user_id.set(9999)
        db.info["audit_user_id"] = 9999
        return MockUser()

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não foi possível validar as credenciais.",
        )
    user = (
        db.query(User)
        .options(joinedload(User.perfil), joinedload(User.perfis), joinedload(User.departamentos))
        .filter(User.id == int(token_data.sub))
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    # Auditoria: o ContextVar não chega ao endpoint (FastAPI roda dependência e
    # endpoint síncronos em threads diferentes), então o usuário vai na sessão do
    # banco, que é a mesma do endpoint na requisição.
    current_user_id.set(user.id)
    db.info["audit_user_id"] = user.id
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo.")
    return current_user

def get_current_active_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not is_diretor_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Privilégios insuficientes."
        )
    return current_user

def get_current_diretor_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not is_diretor_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Apenas Diretores podem realizar esta ação."
        )
    return current_user

def get_current_analista_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    from app.core.module_write import WRITE_BLOCK_DETAIL, can_write_module
    if not can_write_module(current_user, "Rentabilidade de Produtos"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=WRITE_BLOCK_DETAIL,
        )
    return current_user

# ==========================================
# NOVAS DEPENDÊNCIAS - FASE 1 (MÓDULO DE ORÇAMENTO)
# ==========================================
from fastapi import Request

class RoleChecker:
    """Valida dinamicamente se o usuário possui os perfis exigidos"""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)):
        # Admin sempre passa
        if is_admin_user(user):
            return user
        eff = effective_role(user)
        if eff not in self.allowed_roles and user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operação não permitida. Perfis exigidos: {self.allowed_roles}"
            )
        return user

# Só is_admin passa (Administrador / ADMIN / Desenvolvedor)
require_admin = RoleChecker([])

def get_active_department_id(request: Request) -> int:
    """Extrai o contexto ativo do Header HTTP"""
    dept_id = (
        request.headers.get("X-Department-Id")
        or request.headers.get("Departamento-Ativo")
    )
    if not dept_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Department-Id' é obrigatório para operações com contexto."
        )
    try:
        return int(dept_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O 'X-Department-Id' deve ser um número inteiro."
        )

def get_active_department(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verifica se o usuário tem permissão para atuar no departamento requisitado (Regra 3 / DEC-006)
    """
    dept_id = get_active_department_id(request)

    from app.services.departamento_leitura import (
        DEPARTAMENTO_TODOS_ID,
        departamento_sentinela_diretoria,
        departamento_sentinela_todos,
        membros_ids_diretoria,
        rejeitar_gravacao_contexto,
    )

    if dept_id == DEPARTAMENTO_TODOS_ID:
        if not can_see_all_departments(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para atuar neste departamento/contexto.",
            )
        sentinela = departamento_sentinela_todos()
        rejeitar_gravacao_contexto(sentinela, request.method)
        return sentinela

    if dept_id < 0:
        from app.models.departamento import Diretoria

        di = db.query(Diretoria).filter(Diretoria.id == -dept_id, Diretoria.ativo == True).first()  # noqa: E712
        if not di:
            raise HTTPException(status_code=404, detail="Diretoria não encontrada.")
        sentinela = departamento_sentinela_diretoria(db, di.id)
        membros = membros_ids_diretoria(db, sentinela)
        if not can_see_all_departments(user):
            if not membros or any(
                not user_has_department_access(user, db, mid) for mid in membros
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para atuar nesta diretoria.",
                )
        rejeitar_gravacao_contexto(sentinela, request.method)
        return sentinela

    if can_see_all_departments(user):
        from app.models.departamento import Departamento
        dept = db.query(Departamento).filter(Departamento.id == dept_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Departamento não encontrado.")
        return dept
        
    if not user_has_department_access(user, db, dept_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atuar neste departamento/contexto.",
        )

    from app.models.departamento import Departamento
    dept = db.query(Departamento).filter(Departamento.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado.")
    return dept
