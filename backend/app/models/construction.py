from sqlalchemy import Column, Integer, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class ViabilityConstruction(Base):
    __tablename__ = "viability_constructions"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # 4 Linhas de Custo Base
    custo_obras = Column(Float, default=0.0)
    custo_obras_tipo = Column(String, default="R$")
    custo_projetos = Column(Float, default=0.0)
    custo_projetos_tipo = Column(String, default="%")
    aquisicao_area = Column(Float, default=0.0)
    aquisicao_area_tipo = Column(String, default="R$")
    adm_obras = Column(Float, default=0.0)
    adm_obras_tipo = Column(String, default="%")

    # Curvas de desembolso físico-financeiro (% por mês) copiadas para congelamento
    curva_obras_json = Column(JSON, default=lambda: {"meses": []})
    curva_projetos_json = Column(JSON, default=lambda: {"meses": []})
    curva_aquisicao_json = Column(JSON, default=lambda: {"meses": []})
    curva_adm_obras_json = Column(JSON, default=lambda: {"meses": []})

    # Custos Extras (Dinamicos)
    extra_constructions_json = Column(JSON, default=lambda: [])

    phase = relationship("Phase", back_populates="construction")
