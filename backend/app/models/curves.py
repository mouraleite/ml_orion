from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class StandardCurve(Base):
    __tablename__ = "standard_curves"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    tipo = Column(String, nullable=False) # 'vendas', 'obras', 'marketing'
    classificacao = Column(String, default="Custo", nullable=False) # 'Custo' ou 'Despesa'
    valores_meses_json = Column(JSON, default=lambda: {"meses": []})

class PhaseCurve(Base):
    __tablename__ = "phase_curves"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    standard_curve_id = Column(Integer, ForeignKey("standard_curves.id", ondelete="CASCADE"), nullable=False)
    mes_inicio = Column(Integer, default=1, nullable=False)

    phase = relationship("Phase", back_populates="curves")
    standard_curve = relationship("StandardCurve")
