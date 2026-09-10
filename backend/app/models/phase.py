from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Phase(Base):
    __tablename__ = "phases"

    id = Column(Integer, primary_key=True, index=True)
    viability_id = Column(Integer, ForeignKey("viabilities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False, default="Fase Única")
    
    curva_vendas_id = Column(Integer, ForeignKey("standard_curves.id", ondelete="SET NULL"), nullable=True)
    curva_obras_id = Column(Integer, ForeignKey("standard_curves.id", ondelete="SET NULL"), nullable=True)

    viability = relationship("Viability", back_populates="phases")
    
    # Relacionamentos 1:1 de cada fase com suas respectivas Abas
    revenue = relationship("ViabilityRevenue", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    construction = relationship("ViabilityConstruction", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    expenses = relationship("ViabilityExpenses", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    taxes = relationship("PhaseTaxes", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    exchanges = relationship("PhaseExchanges", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    funding = relationship("PhaseFunding", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    physical_data = relationship("PhasePhysicalData", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    dates = relationship("PhaseDates", back_populates="phase", uselist=False, cascade="all, delete-orphan")

    # Curvas dinâmicas (1:N) — substitui os campos legados curva_vendas_id / curva_obras_id
    curves = relationship("PhaseCurve", back_populates="phase", cascade="all, delete-orphan")

# Importações no final para resolver dependências de string do SQLAlchemy (evitando dependências circulares)
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase_details import PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates
from app.models.curves import PhaseCurve
