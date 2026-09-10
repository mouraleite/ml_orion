from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class Vision(Base):
    """Container nomeado para uma estrutura de visão (cenário DRE)."""
    __tablename__ = "visions"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    is_padrao = Column(Boolean, default=False)  # Visão importada do Sienge, protegida
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Nós da estrutura hierárquica desta visão
    nodes = relationship("VisionNode", back_populates="vision", cascade="all, delete-orphan")


class VisionNode(Base):
    """Categoria/grupo dentro de uma Visão (ex: 01 - RECEITAS)."""
    __tablename__ = "vision_nodes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, index=True)
    descricao = Column(String)

    # FK para a Visão pai
    vision_id = Column(Integer, ForeignKey("visions.id"), nullable=False)
    vision = relationship("Vision", back_populates="nodes")

    # Vínculos com planos financeiros nesta visão
    plan_links = relationship("FinancialPlanVisionLink", back_populates="vision_node", cascade="all, delete-orphan")


class FinancialPlanVisionLink(Base):
    """Vínculo entre um Plano Financeiro e um nó de uma Visão específica."""
    __tablename__ = "fp_vision_links"

    id = Column(Integer, primary_key=True, index=True)
    financial_plan_id = Column(Integer, ForeignKey("planos_financeiros.id"), nullable=False)
    vision_id = Column(Integer, ForeignKey("visions.id"), nullable=False)
    vision_node_id = Column(Integer, ForeignKey("vision_nodes.id"), nullable=True)

    # Relacionamentos
    financial_plan = relationship("FinancialPlan", back_populates="vision_links")
    vision_node = relationship("VisionNode", back_populates="plan_links")
