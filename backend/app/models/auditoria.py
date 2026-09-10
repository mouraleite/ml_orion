from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base
from sqlalchemy.orm import relationship

class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    evento = Column(String, index=True) # Criacao, Alteracao, Reabertura, Aprovacao, Importacao, Integracao
    tabela_afetada = Column(String, index=True, nullable=True)
    registro_id = Column(Integer, nullable=True) # ID do registro alterado
    
    campo = Column(String, nullable=True)
    valor_anterior = Column(String, nullable=True)
    novo_valor = Column(String, nullable=True)
    
    motivo = Column(String, nullable=True) # Para reabertura
    
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User")
