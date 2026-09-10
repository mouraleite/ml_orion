from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class UserDepartamento(Base):
    __tablename__ = "user_departamentos"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), primary_key=True)


class UserPerfil(Base):
    __tablename__ = "user_perfis"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    perfil_id = Column(Integer, ForeignKey("access_profiles.id"), primary_key=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    cpf = Column(String, unique=True, index=True, nullable=True)
    departamento = Column(String, nullable=True) # Legado, mantido para evitar quebra
    cargo = Column(String, nullable=True)
    nivel = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    sienge_id = Column(Integer, nullable=True)
    microsoft_oid = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    role = Column(String, default="Usuario", nullable=False) # "Administrador", "Gestor", "Usuario", "Consulta", "Integracao"
    is_active = Column(Boolean, default=True)

    # Nova relação multi-contexto (DEC-006)
    departamentos = relationship("Departamento", secondary="user_departamentos", backref="usuarios")
    
    perfil_id = Column(Integer, ForeignKey("access_profiles.id"), nullable=True)
    perfil = relationship("AccessProfile", back_populates="users", foreign_keys=[perfil_id])
    perfis = relationship("AccessProfile", secondary="user_perfis")
