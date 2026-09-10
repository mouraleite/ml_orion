from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base
from sqlalchemy.orm import relationship

class ClosedMonth(Base):
    __tablename__ = "fechamento_meses"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False) # 1 a 12
    fechado_por_id = Column(Integer, ForeignKey("users.id"))
    data_fechamento = Column(DateTime, default=datetime.utcnow)

    fechado_por = relationship("User")
