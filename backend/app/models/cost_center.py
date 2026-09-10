from sqlalchemy import Column, Integer, String, JSON, Boolean, Float
from app.db.database import Base

class CostCenter(Base):
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True, index=True)
    id_sienge = Column(String, unique=True, index=True)
    nome = Column(String)
    status = Column(String, default="Ativo")
    
    # Guarda os dados dinâmicos das colunas customizadas
    # Ex: {"Observações": "algum texto", "Prioridade": "Alta"}
    custom_data = Column(JSON, default={})

    # Campos de Acompanhamento / Integração (ERP -> Dashboard)
    track_in_dashboard = Column(Boolean, default=False)
    project_phase = Column(String, default="Em Andamento") # Em Andamento, Encerrado
    manual_land_cost = Column(Float, default=0.0)
    
    # Rateio: [{"viability_id": 1, "rule_type": "VGV", "percentage": 100.0}]
    apportionment_rules = Column(JSON, default=[])

    # Parceria (Visão de Rateio)
    partnership_config_id = Column(Integer, default=None)
