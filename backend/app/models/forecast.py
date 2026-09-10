from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    ano = Column(Integer, index=True)
    tipo = Column(String) # DESPESAS ou VENDAS
    mes_corte = Column(Integer) # Mês a partir do qual é editável
    versao_numero = Column(Integer, default=1)
    status = Column(String, default="Rascunho") 
    usuario_criador_id = Column(Integer, ForeignKey("users.id"))
    data_criacao = Column(DateTime, default=datetime.utcnow)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    produto_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True)  # Fase 2: granularidade produto-a-produto
    
    # N:1 versão-base (pode ser Orcamento ou outro Forecast)
    versao_base_orcamento_id = Column(Integer, ForeignKey("orcamentos.id"), nullable=True)
    versao_base_forecast_id = Column(Integer, ForeignKey("forecasts.id"), nullable=True)

    motivo_reabertura = Column(String, nullable=True)

    # Bloqueio Pessimista (COM-009)
    usuario_edicao_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    data_inicio_edicao = Column(DateTime, nullable=True)
    # Relações
    itens_despesa = relationship("ForecastItem", back_populates="forecast", cascade="all, delete-orphan")
    itens_venda = relationship("ForecastVendaItem", back_populates="forecast", cascade="all, delete-orphan")
    usuario_criador = relationship("User", foreign_keys=[usuario_criador_id])
    usuario_edicao = relationship("User", foreign_keys=[usuario_edicao_id])
    departamento = relationship("Departamento")
    produto = relationship("CostCenter", foreign_keys=[produto_id])
    versao_base_orcamento = relationship("Orcamento")
    # versao_base_forecast resolvido automaticamente pelo SQLAlchemy, mas podemos adicionar:
    versao_base_forecast = relationship("Forecast", remote_side=[id])

class ForecastItem(Base):
    __tablename__ = "forecast_itens"

    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id"))
    produto_id = Column(Integer, ForeignKey("cost_centers.id"))
    plano_financeiro_id = Column(Integer, ForeignKey("planos_financeiros.id"))
    
    # Valores mensais
    jan = Column(Float, default=0.0)
    fev = Column(Float, default=0.0)
    mar = Column(Float, default=0.0)
    abr = Column(Float, default=0.0)
    mai = Column(Float, default=0.0)
    jun = Column(Float, default=0.0)
    jul = Column(Float, default=0.0)
    ago = Column(Float, default=0.0)
    set = Column(Float, default=0.0)
    out = Column(Float, default=0.0)
    nov = Column(Float, default=0.0)
    dez = Column(Float, default=0.0)

    total_anual = Column(Float, default=0.0)
    observacao = Column(String, nullable=True)
    is_auto_generated = Column(Boolean, default=False)

    forecast = relationship("Forecast", back_populates="itens_despesa")
    produto = relationship("CostCenter")
    plano_financeiro = relationship("FinancialPlan")

class ForecastVendaItem(Base):
    __tablename__ = "forecast_venda_itens"

    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id"))
    produto_id = Column(Integer, ForeignKey("cost_centers.id"))
    plano_venda_id = Column(Integer, ForeignKey("payment_plans.id"))
    
    mes = Column(Integer)
    ano = Column(Integer)
    
    juros_mensal = Column(Float, default=0.0)
    ticket_medio = Column(Float, default=0.0)
    numero_vendas = Column(Integer, default=0)
    vgv = Column(Float, default=0.0)
    origem_venda = Column(String, nullable=True)
    
    observacao = Column(String, nullable=True)

    forecast = relationship("Forecast", back_populates="itens_venda")
    produto = relationship("CostCenter")
    plano_venda = relationship("PaymentPlan")
