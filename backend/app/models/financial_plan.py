from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class FinancialPlan(Base):
    __tablename__ = "planos_financeiros"

    id = Column(Integer, primary_key=True, index=True)
    db_id = Column(String, unique=True, index=True) # ID from Sienge
    name = Column(String, index=True)
    tp_conta = Column(String) # R or T
    fl_redutora = Column(String) # S or N
    fl_ativa = Column(String) # S or N
    fl_adiantamento = Column(String) # S or N
    fl_imposto = Column(String) # S or N

    # Relacionamento com Orçamento (One-to-Many)
    orcamentos = relationship("OrcamentoItem", back_populates="plano_financeiro")

    # Vínculos com Visões (múltiplos cenários)
    vision_links = relationship("FinancialPlanVisionLink", back_populates="financial_plan", cascade="all, delete-orphan")

    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Importação no final para resolver referências em string do SQLAlchemy
from app.models.vision import FinancialPlanVisionLink
from app.models.orcamento import OrcamentoItem
