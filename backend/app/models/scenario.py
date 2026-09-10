from sqlalchemy import Column, Integer, String, Float
from app.db.database import Base

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    
    # Multiplicadores de Simulação (default 1.0 = 100%)
    vgv_multiplier = Column(Float, default=1.0)
    construction_cost_multiplier = Column(Float, default=1.0)
    sales_speed_multiplier = Column(Float, default=1.0)
