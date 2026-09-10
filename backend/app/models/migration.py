from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.database import Base

class MigrationMapping(Base):
    __tablename__ = "migration_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, index=True) # "CENTRO_CUSTO" ou "PLANO_FINANCEIRO"
    nome_origem = Column(String, index=True) # Nome exato que veio na planilha
    id_destino = Column(Integer, nullable=True) # ID no ERP ML associado
    status = Column(String, default="PENDING") # "PENDING" ou "MAPPED"
    data_criacao = Column(DateTime, default=datetime.utcnow)
