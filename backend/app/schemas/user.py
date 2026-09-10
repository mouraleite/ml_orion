from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Base Properties
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    cpf: Optional[str] = None
    departamento: Optional[str] = None
    cargo: Optional[str] = None
    nivel: Optional[str] = None
    avatar: Optional[str] = None
    sienge_id: Optional[int] = None
    role: str = "READ_ONLY"
    perfil_id: Optional[int] = None

class DepartamentoSimples(BaseModel):
    id: int
    nome: str
    is_residual: bool = False
    diretoria_id: Optional[int] = None
    model_config = {"from_attributes": True}


class DiretoriaSimples(BaseModel):
    id: int
    nome: str
    departamento_ids: List[int] = []
    model_config = {"from_attributes": True}

# Propriedades para criação (senha opcional = SSO Microsoft)
class UserCreate(UserBase):
    password: Optional[str] = None
    departamento_ids: List[int] = []
    perfil_ids: List[int] = []

class PerfilSimples(BaseModel):
    id: int
    name: str
    permissions: dict
    model_config = {"from_attributes": True}


class UserCapabilities(BaseModel):
    admin: bool = False
    diretor: bool = False
    gestor: bool = False
    analista: bool = False


# Propriedades para resposta (esconde a senha)
class UserResponse(UserBase):
    id: int
    is_active: bool
    departamentos: List[DepartamentoSimples] = []
    diretorias: List[DiretoriaSimples] = []
    perfil: Optional[PerfilSimples] = None
    perfis: List[PerfilSimples] = []
    perfil_ids: List[int] = []
    effective_role: Optional[str] = None
    capabilities: Optional[UserCapabilities] = None
    pode_ver_todos_departamentos: bool = False
    pode_consolidacao_mldu_orcamento: bool = False
    pode_consolidacao_mldu_forecast: bool = False
    write_modules: dict[str, bool] = {}

    model_config = {"from_attributes": True}

# Propriedades para atualização
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    cpf: Optional[str] = None
    departamento: Optional[str] = None
    cargo: Optional[str] = None
    nivel: Optional[str] = None
    avatar: Optional[str] = None
    sienge_id: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    perfil_id: Optional[int] = None
    perfil_ids: Optional[List[int]] = None
    departamento_ids: Optional[List[int]] = None

# Tokens
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
