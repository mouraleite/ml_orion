from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class EconomicIndex(Base):
    __tablename__ = "economic_indices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # Ex: INCC, Selic, CDI, WACC
    symbol = Column(String, default="%") # Ex: %, R$
    current_value = Column(Float, nullable=False, default=0.0)
    projected_value = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
