from sqlalchemy import Column, Integer, String, JSON
from app.db.database import Base

class PaymentPlan(Base):
    __tablename__ = "payment_plans"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    condicoes_json = Column(JSON, default=lambda: []) # Lista de condições {"nome": "A VISTA", "perc": 3.8}
