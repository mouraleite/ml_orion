from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from app.db.tipos import Dinheiro

class Orcamento(Base):
    __tablename__ = "orcamentos"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    ano = Column(Integer, index=True)
    tipo = Column(String, default="DESPESAS") # "DESPESAS" ou "VENDAS"
    status = Column(String, default="Rascunho") # Rascunho, Em aprovação, Aprovado, Fechado, Reaberto
    versao_numero = Column(Integer, default=1)
    versao_base_id = Column(Integer, ForeignKey("orcamentos.id"), nullable=True)
    usuario_criador_id = Column(Integer, ForeignKey("users.id"))
    data_criacao = Column(DateTime, default=datetime.utcnow)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    produto_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True)  # Fase 2: granularidade produto-a-produto
    motivo_reabertura = Column(String, nullable=True)

    # Bloqueio Pessimista (COM-009)
    usuario_edicao_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    data_inicio_edicao = Column(DateTime, nullable=True)

    # Relações
    itens_despesa = relationship("OrcamentoItem", back_populates="orcamento", cascade="all, delete-orphan")
    itens_venda = relationship("OrcamentoVendaItem", back_populates="orcamento", cascade="all, delete-orphan")
    usuario_criador = relationship("User", foreign_keys=[usuario_criador_id])
    usuario_edicao = relationship("User", foreign_keys=[usuario_edicao_id])
    departamento = relationship("Departamento")
    produto = relationship("CostCenter", foreign_keys=[produto_id])
    versao_base = relationship("Orcamento", remote_side=[id])

class OrcamentoHistorico(Base):
    __tablename__ = "orcamento_historico"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id"))
    usuario_id = Column(Integer, ForeignKey("users.id"))
    status_anterior = Column(String)
    status_novo = Column(String)
    motivo = Column(String, nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)

    orcamento = relationship("Orcamento")
    usuario = relationship("User")

class OrcamentoItem(Base):
    __tablename__ = "orcamento_itens"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id"))
    produto_id = Column(Integer, ForeignKey("cost_centers.id"))
    plano_financeiro_id = Column(Integer, ForeignKey("planos_financeiros.id"))
    
    # Valores mensais
    jan = Column(Dinheiro, default=0.0)
    fev = Column(Dinheiro, default=0.0)
    mar = Column(Dinheiro, default=0.0)
    abr = Column(Dinheiro, default=0.0)
    mai = Column(Dinheiro, default=0.0)
    jun = Column(Dinheiro, default=0.0)
    jul = Column(Dinheiro, default=0.0)
    ago = Column(Dinheiro, default=0.0)
    set = Column(Dinheiro, default=0.0)
    out = Column(Dinheiro, default=0.0)
    nov = Column(Dinheiro, default=0.0)
    dez = Column(Dinheiro, default=0.0)

    total_anual = Column(Dinheiro, default=0.0)
    observacao = Column(String, nullable=True)

    orcamento = relationship("Orcamento", back_populates="itens_despesa")
    produto = relationship("CostCenter")
    plano_financeiro = relationship("FinancialPlan")

class OrcamentoVendaItem(Base):
    __tablename__ = "orcamento_venda_itens"

    id = Column(Integer, primary_key=True, index=True)
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id"))
    produto_id = Column(Integer, ForeignKey("cost_centers.id"))
    plano_venda_id = Column(Integer, ForeignKey("payment_plans.id"))
    
    mes = Column(Integer) # 1 a 12
    ano = Column(Integer)
    
    juros_mensal = Column(Float, default=0.0)
    ticket_medio = Column(Dinheiro, default=0.0)
    numero_vendas = Column(Integer, default=0)
    vgv = Column(Dinheiro, default=0.0)
    origem_venda = Column(String, nullable=True)
    
    observacao = Column(String, nullable=True)

    orcamento = relationship("Orcamento", back_populates="itens_venda")
    produto = relationship("CostCenter")
    plano_venda = relationship("PaymentPlan")
