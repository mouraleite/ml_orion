from sqlalchemy import Column, Integer, String, JSON
from app.db.database import Base

class PartnershipConfig(Base):
    __tablename__ = "partnership_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    sienge_prefix = Column(String, unique=True, index=True)
    
    # JSON containing the apportionment rules.
    # Format: {"RECEITA BRUTA": {"empreendedor": 50.0, "parceiro": 50.0}, "CUSTO DE OBRA": {"empreendedor": 100.0, "parceiro": 0.0}}
    # Any node not listed defaults to 100% Empreendedor.
    rules = Column(JSON, default={})
