"""Saldo de conta corrente no 31/12 fechado (Sienge accounts-balances).

Chave = id Sienge da empresa + número da conta + data. Só tipos B+I+C entram.
Não alimenta orçamento, forecast nem rentabilidade — só o card de geração de caixa.
"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Index, Integer, String, UniqueConstraint

from app.db.database import Base


class SiengeAccountBalance(Base):
    __tablename__ = "sienge_account_balances"

    id = Column(Integer, primary_key=True)
    company_id_sienge = Column(String, nullable=False, index=True)
    account_number = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    account_type = Column(String(8), nullable=False, index=True)
    balance_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "company_id_sienge",
            "account_number",
            "balance_date",
            name="uq_sienge_account_balances_key",
        ),
        Index("ix_sienge_account_balances_date_type", "balance_date", "account_type"),
    )
