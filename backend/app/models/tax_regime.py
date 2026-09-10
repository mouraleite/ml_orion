from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class TaxRegime(Base):
    __tablename__ = "tax_regimes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    pis = Column(Float, default=0.0)
    cofins = Column(Float, default=0.0)
    irpj = Column(Float, default=0.0)
    csll = Column(Float, default=0.0)
    outros = Column(Float, default=0.0)
    ativo = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
