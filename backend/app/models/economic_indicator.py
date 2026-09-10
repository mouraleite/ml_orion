from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class EconomicIndicator(Base):
    __tablename__ = "economic_indicators"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    index_type = Column(String)  # "IPCA" ou "INCC"
    valor = Column(Float)
    tipo_unidade = Column(String)  # "% a.a." ou "% a.m."
    competencia = Column(String, nullable=True) # Ex: "05/2024"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
