from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class DepartamentoCostCenter(Base):
    """Whitelist: Centros de Custo que o Departamento pode enxergar/editar"""
    __tablename__ = "departamento_cost_centers"

    id = Column(Integer, primary_key=True, index=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"))
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"))
    permitido = Column(Boolean, default=True)

    departamento = relationship("Departamento", back_populates="cost_centers")
    cost_center = relationship("CostCenter")


class Diretoria(Base):
    """Agrupa departamentos. Um departamento pertence a no máximo uma diretoria."""

    __tablename__ = "diretorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    ativo = Column(Boolean, default=True, nullable=False)

    departamentos = relationship("Departamento", back_populates="diretoria")


class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    ativo = Column(Boolean, default=True)
    is_residual = Column(Boolean, default=False, nullable=False)
    diretoria_id = Column(Integer, ForeignKey("diretorias.id"), nullable=True, index=True)

    planos = relationship("DepartamentoPlano", back_populates="departamento")
    cost_centers = relationship("DepartamentoCostCenter", back_populates="departamento")
    diretoria = relationship("Diretoria", back_populates="departamentos")

class DepartamentoPlano(Base):
    __tablename__ = "departamento_planos"

    id = Column(Integer, primary_key=True, index=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"))
    plano_financeiro_id = Column(Integer, ForeignKey("planos_financeiros.id"))
    permitido = Column(Boolean, default=True)

    departamento = relationship("Departamento", back_populates="planos")
    plano_financeiro = relationship("FinancialPlan")

class DeparaAutorizacaoDepartamento(Base):
    """Casamento name Sienge (autorização /department) → departamento do Apoio.

    departamento_id nulo = Corporativo (residual). definido_manual impede o sync de sobrescrever.
    """

    __tablename__ = "depara_autorizacao_departamento"

    id = Column(Integer, primary_key=True, index=True)
    nome_sienge = Column(String, unique=True, nullable=False, index=True)
    sienge_department_id = Column(Integer, nullable=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    definido_manual = Column(Boolean, default=False, nullable=False)

    departamento = relationship("Departamento")


class ProdutoPlanoFinanceiro(Base):
    __tablename__ = "produto_plano_financeiro"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("cost_centers.id"))
    plano_financeiro_id = Column(Integer, ForeignKey("planos_financeiros.id"))
    permitido = Column(Boolean, default=True)

    produto = relationship("CostCenter")
    plano_financeiro = relationship("FinancialPlan")
