from sqlalchemy import Column, Integer, String
from app.db.database import Base

class SiengeColaborador(Base):
    __tablename__ = "sienge_colaboradores"

    id = Column(Integer, primary_key=True, index=True)
    sienge_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    trade_name = Column(String, nullable=True)
    cpf = Column(String, nullable=True)
    phone_ddd = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address_json = Column(String, nullable=True) # Storing full address as string JSON
    email = Column(String, nullable=True)
