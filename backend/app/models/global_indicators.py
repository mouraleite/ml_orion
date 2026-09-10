from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class GlobalIndicators(Base):
    __tablename__ = "global_indicators"

    id = Column(Integer, primary_key=True, index=True)
    ipca_padrao_valor = Column(Float, default=4.5)
    ipca_padrao_tipo = Column(String, default="% a.a.")
    incc_padrao_valor = Column(Float, default=5.0)
    incc_padrao_tipo = Column(String, default="% a.a.")
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
