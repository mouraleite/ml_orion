from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.core import security
from app.core.user_identity import digits_only, is_sienge_colab_registered
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, DepartamentoSimples, DiretoriaSimples
from app.services.sienge_api import get_departamentos
from app.services.user_department_scope import (
    can_see_all_departments,
    departamentos_for_user,
    diretorias_for_user,
    first_departamento_nome,
    sync_user_departamentos,
)
from app.services.user_perfis import sync_user_perfis
from app.services.user_response import attach_user_perfis

router = APIRouter()


def _user_load_options():
    return (joinedload(User.departamentos), joinedload(User.perfil), joinedload(User.perfis))


def _resolve_perfil_ids(perfil_ids: list[int] | None, perfil_id: int | None) -> list[int]:
    if perfil_ids:
        return [int(x) for x in perfil_ids]
    if perfil_id:
        return [int(perfil_id)]
    return []


def _reload_user(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(*_user_load_options())
        .filter(User.id == user_id)
        .first()
    )


def _user_response(db: Session, user: User) -> UserResponse:
    resp = UserResponse.model_validate(user)
    resp.pode_ver_todos_departamentos = can_see_all_departments(user)
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


def _duplicate_user_message(
    users: list[User],
    *,
    email: str | None,
    cpf: str | None,
    sienge_id: int | None,
) -> str | None:
    if sienge_id is not None and any(u.sienge_id == sienge_id for u in users):
        return "Este colaborador do Sienge já está cadastrado."
    cpf_d = digits_only(cpf)
    if len(cpf_d) == 11 and any(digits_only(u.cpf) == cpf_d for u in users):
        return "Já existe um colaborador com este CPF."
    if email:
        needle = email.strip().lower()
        if any((u.email or "").strip().lower() == needle for u in users):
            return "O usuário com este e-mail já existe."
    return None

@router.get("/", response_model=List[UserResponse])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.require_admin),
) -> Any:
    """Lista usuários (somente administrador)."""
    users = (
        db.query(User)
        .options(*_user_load_options())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_user_response(db, user) for user in users]

@router.post("/", response_model=UserResponse)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.require_admin),
) -> Any:
    """Cria um novo usuário (somente administrador)."""
    others = db.query(User).all()
    conflict = _duplicate_user_message(
        others,
        email=user_in.email,
        cpf=user_in.cpf,
        sienge_id=user_in.sienge_id,
    )
    if conflict:
        raise HTTPException(status_code=400, detail=conflict)
    raw_password = (user_in.password or "").strip()
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(raw_password) if raw_password else None,
        full_name=user_in.full_name,
        cpf=user_in.cpf,
        departamento=user_in.departamento,
        cargo=user_in.cargo,
        nivel=user_in.nivel,
        avatar=user_in.avatar,
        sienge_id=user_in.sienge_id,
        role=user_in.role,
        perfil_id=None,
    )
    db.add(user)
    db.flush()
    if user_in.departamento_ids:
        sync_user_departamentos(db, user.id, user_in.departamento_ids)
        nome = first_departamento_nome(db, user_in.departamento_ids)
        if nome:
            user.departamento = nome
    sync_user_perfis(db, user.id, _resolve_perfil_ids(user_in.perfil_ids, user_in.perfil_id))
    db.commit()
    loaded = _reload_user(db, user.id)
    return _user_response(db, loaded or user)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(deps.require_admin),
) -> Any:
    """Atualiza um usuário existente (somente administrador)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    update_data = user_in.model_dump(exclude_unset=True)
    departamento_ids = update_data.pop("departamento_ids", None)
    perfil_ids = update_data.pop("perfil_ids", None)
    has_perfil_id = "perfil_id" in update_data
    perfil_id_val = update_data.pop("perfil_id", None)

    if "password" in update_data and update_data["password"]:
        hashed_password = security.get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    elif "password" in update_data:
        del update_data["password"]

    if departamento_ids is not None:
        update_data.pop("departamento", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    if departamento_ids is not None:
        sync_user_departamentos(db, user.id, departamento_ids)
        user.departamento = first_departamento_nome(db, departamento_ids)

    if perfil_ids is not None:
        sync_user_perfis(db, user.id, perfil_ids)
    elif has_perfil_id:
        sync_user_perfis(db, user.id, _resolve_perfil_ids(None, perfil_id_val))

    db.add(user)
    db.commit()
    loaded = _reload_user(db, user.id)
    return _user_response(db, loaded or user)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.require_admin),
) -> Any:
    """Remove um usuário (somente administrador)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.delete(user)
    db.commit()
    return user

@router.get("/sienge/colaboradores")
def read_sienge_colaboradores(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Colaboradores Sienge ainda não cadastrados no sistema."""
    from app.models.sienge_colaborador import SiengeColaborador

    existentes = db.query(User).all()
    colabs = db.query(SiengeColaborador).all()
    return [
        {
            "id": c.sienge_id,
            "name": c.name,
            "cpf": c.cpf,
            "email": c.email or "",
            "trade_name": c.trade_name,
            "phone_ddd": c.phone_ddd,
            "phone_number": c.phone_number,
            "address_json": c.address_json,
        }
        for c in colabs
        if not is_sienge_colab_registered(c, existentes)
    ]

@router.get("/sienge/departamentos")
def read_sienge_departamentos(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Departamentos Sienge (usuário autenticado)."""
    return get_departamentos()
