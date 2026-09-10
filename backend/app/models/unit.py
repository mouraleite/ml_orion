from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Unit(Base):
    """
    Unidades (Lotes, Apartamentos, etc) de um Centro de Custo.
    Usadas para calcular R$/m2 e projetar receitas futuras do estoque.
    """
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="CASCADE"), index=True)
    
    # ID do Sienge para esta unidade
    id_sienge = Column(Integer, index=True)
    
    # Nome da Unidade (Ex: "F-286")
    name = Column(String, index=True)
    
    # Status (Ex: "D" para Disponível, "V" para Vendido) - mapeado do commercialStock
    status = Column(String)
    
    # Área Privativa em m2
    private_area = Column(Float, default=0.0)

    # Relacionamentos
    cost_center = relationship("CostCenter")
    transactions = relationship("ActualTransaction", back_populates="unit")
