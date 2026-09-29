from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String

from app.db.database import Base


class SiengeApiCall(Base):
    """Chamada HTTP deste ERP à API Sienge. Não entra em orçamento, forecast ou rentabilidade."""

    __tablename__ = "sienge_api_calls"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    family = Column(String(8), nullable=False, index=True)
    method = Column(String(8), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_sienge_api_calls_created_family", "created_at", "family"),
    )
