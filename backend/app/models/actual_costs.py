from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class ActualCost(Base):
    __tablename__ = "actual_costs"

    id = Column(Integer, primary_key=True, index=True)
    viability_id = Column(Integer, ForeignKey("viabilities.id", ondelete="CASCADE"), nullable=False)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="CASCADE"), nullable=False)
    
    # Detalhes da transação
    document_date = Column(Date, nullable=True) # Data de emissão/pagamento
    document_number = Column(String, nullable=True)
    category = Column(String, nullable=False) # Ex: "Obras" (precisamos cruzar as rubricas)
    
    total_value = Column(Float, default=0.0) # Valor original do Sienge
    apportionment_percentage = Column(Float, default=100.0) # % de rateio
    value_apportioned = Column(Float, default=0.0) # total_value * (apportionment_percentage / 100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    viability = relationship("Viability", backref="actual_costs")
    cost_center = relationship("CostCenter", backref="actual_costs")
