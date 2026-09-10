from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class AccessProfile(Base):
    __tablename__ = "access_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default=dict) # {"Apoio": {"Empresas": true, ...}, ...}

    users = relationship("User", back_populates="perfil", foreign_keys="User.perfil_id")
