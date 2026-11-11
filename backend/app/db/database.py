from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


def is_sqlite_url(url: str | None = None) -> bool:
    return (url or settings.DATABASE_URL).startswith("sqlite")


def is_postgres_url(url: str | None = None) -> bool:
    u = (url or settings.DATABASE_URL).lower()
    return u.startswith("postgresql") or u.startswith("postgres://")


# Engine do SQLAlchemy
if is_sqlite_url():
    from sqlalchemy import event
    engine = create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        # Conexões paradas por minutos (sync) eram derrubadas pelo Neon (11/11/2026).
        pool_recycle=300,
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def load_models():
    """Garante que todos os models entram no Base.metadata (Alembic e create_all)."""
    import importlib

    for name in (
        "access_profile",
        "actual_costs",
        "actual_transaction",
        "actuals",
        "auditoria",
        "company",
        "construction",
        "cost_center",
        "curves",
        "custom_field",
        "departamento",
        "economic_indicator",
        "expenses",
        "fechamento",
        "financial_plan",
        "forecast",
        "global_indicators",
        "governance",
        "integracao",
        "migration",
        "orcamento",
        "partnership",
        "payment_plan",
        "phase",
        "phase_details",
        "revenue",
        "scenario",
        "sienge_account_balance",
        "sienge_api_call",
        "sienge_colaborador",
        "snapshot",
        "system_settings",
        "tax_regime",
        "unit",
        "user",
        "viability",
        "vision",
    ):
        importlib.import_module(f"app.models.{name}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    load_models()
    Base.metadata.create_all(bind=engine)
    from app.db.schema_patches import apply_schema_patches

    apply_schema_patches(engine)

