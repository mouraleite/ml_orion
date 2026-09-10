"""
Prepara Postgres vazio: create_all + alembic stamp head.

Uso (backend/, venv ativo, docker-compose up -d db):

  python scripts/postgres_init.py

Requer DATABASE_URL apontando para Postgres no .env.
Não altera SQLite. Não roda upgrade com revisão autogerada.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.database import engine, init_db, is_postgres_url, load_models


def main() -> int:
    if not is_postgres_url():
        print("DATABASE_URL não é Postgres. Ajuste backend/.env antes de continuar.")
        print(f"  Atual: {settings.DATABASE_URL}")
        return 1

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"Não foi possível conectar ao Postgres: {exc}")
        print("Suba o container: docker-compose up -d db")
        return 1

    load_models()
    init_db()
    tables = inspect(engine).get_table_names()
    print(f"Schema OK ({len(tables)} tabelas visíveis).")

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.stamp(alembic_cfg, "head")
    print("Alembic: stamp head (20260828_baseline).")
    print("Próximo passo opcional: python scripts/sqlite_para_postgres.py --confirm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
