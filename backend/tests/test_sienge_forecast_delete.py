"""A limpeza de previsão tem que funcionar no Postgres (boolean), não só no SQLite."""

from datetime import date

from sqlalchemy.dialects import postgresql

from app.models.actual_transaction import ActualTransaction
from app.services.sienge_sync import _clear_open_forecast


def test_delete_forecast_usa_boolean_no_postgres():
    stmt = ActualTransaction.__table__.delete().where(
        ActualTransaction.cost_center_id == 1,
        ActualTransaction.transaction_type == "INCOME",
        ActualTransaction.is_forecast.is_(True),
    )
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "is_forecast IS true" in sql or "is_forecast IS TRUE" in sql
    assert "is_forecast = 1" not in sql


def test_clear_open_forecast_apaga_so_previsao(db_session):
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="FCST-INC-1",
            transaction_type="INCOME",
            transaction_date=date(2026, 10, 19),
            value=10,
            category="Receita",
            is_forecast=True,
        )
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="INC-1",
            transaction_type="INCOME",
            transaction_date=date(2026, 10, 19),
            value=20,
            category="Receita",
            is_forecast=False,
        )
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="TRK-VENC-INC-9-1",
            transaction_type="INCOME",
            transaction_date=date(2026, 9, 15),
            value=30,
            category="Receita",
            is_forecast=True,
        )
    )
    db_session.commit()

    _clear_open_forecast(db_session, 1, "INCOME")

    left = {row.source_id for row in db_session.query(ActualTransaction).filter_by(cost_center_id=1).all()}
    assert left == {"INC-1", "TRK-VENC-INC-9-1"}
