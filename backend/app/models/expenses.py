from sqlalchemy import Column, Integer, Float, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class ViabilityExpenses(Base):
    __tablename__ = "viability_expenses"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Valores sobre o VGV ou Absolutos
    marketing_valor = Column(Float, default=5.0)
    marketing_tipo = Column(String, default="%")
    comercial_valor = Column(Float, default=1.0)
    comercial_tipo = Column(String, default="%")
    comissao_corretagem_valor = Column(Float, default=0.0)
    adm_valor = Column(Float, default=3.0)
    adm_tipo = Column(String, default="%")

    # Curvas de Despesa (% por mês para distribuir a verba)
    curva_marketing_json = Column(JSON, default=lambda: {"meses": []})
    curva_comercial_json = Column(JSON, default=lambda: {"meses": []})
    curva_adm_json = Column(JSON, default=lambda: {"meses": []})

    # Despesas Extras (Dinamicas)
    extra_expenses_json = Column(JSON, default=lambda: [])

    phase = relationship("Phase", back_populates="expenses")
