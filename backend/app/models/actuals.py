from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.phase import Base

class PhaseActuals(Base):
    __tablename__ = "phase_actuals"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    
    # Ex: "Receitas", "Obras", "Terreno", "Impostos", "Comercial", "Administrativo", "Funding"
    categoria = Column(String, nullable=False, index=True) 
    
    mes_referencia = Column(Integer, nullable=False) # Ex: 1, 2, 3 (mês do cronograma) ou um YYYYMM
    valor_realizado = Column(Float, default=0.0)
    
    observacao = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    phase = relationship("Phase", backref="actuals")
