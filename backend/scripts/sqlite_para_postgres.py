"""
Copia dados do SQLite local para Postgres (schema já criado).

Uso:

  python scripts/postgres_init.py
  python scripts/sqlite_para_postgres.py --confirm
  python scripts/postgres_comparar.py

  python scripts/sqlite_para_postgres.py --sqlite ./viabilidades.db --confirm

Requer DATABASE_URL (Postgres) no .env. Não apaga o arquivo SQLite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text

from app.core.config import settings
from app.db.database import Base, is_postgres_url, is_sqlite_url, load_models


def _sqlite_url_from_path(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _reset_sequences(pg_engine, table_names: list[str]) -> None:
    with pg_engine.begin() as conn:
        for name in table_names:
            try:
                conn.execute(
                    text(
                        f"""
                        SELECT setval(
                            pg_get_serial_sequence('"{name}"', 'id'),
                            COALESCE((SELECT MAX(id) FROM "{name}"), 1),
                            (SELECT COUNT(*) > 0 FROM "{name}")
                        )
                        """
                    )
                )
            except Exception:
                pass


def copy_data(sqlite_url: str, postgres_url: str) -> dict[str, int]:
    load_models()
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    pg_engine = create_engine(postgres_url, pool_pre_ping=True)

    Base.metadata.create_all(pg_engine)

    tables = [
        t for t in Base.metadata.sorted_tables
        if t.name != "alembic_version"
    ]
    counts: dict[str, int] = {}

    with pg_engine.begin() as pg_conn:
        for table in reversed(tables):
            if inspect(pg_engine).has_table(table.name):
                pg_conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))

    with sqlite_engine.connect() as src, pg_engine.begin() as dst:
        for table in tables:
            if not inspect(sqlite_engine).has_table(table.name):
                counts[table.name] = 0
                continue
            rows = src.execute(select(table)).mappings().all()
            counts[table.name] = len(rows)
            if rows:
                dst.execute(table.insert(), [dict(r) for r in rows])

    _reset_sequences(pg_engine, [t.name for t in tables])

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.stamp(alembic_cfg, "head")

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Copia SQLite → Postgres")
    parser.add_argument(
        "--sqlite",
        default=str(Path(__file__).resolve().parents[1] / "viabilidades.db"),
        help="Caminho do arquivo SQLite de origem",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Obrigatório: confirma TRUNCATE + cópia no Postgres alvo",
    )
    args = parser.parse_args()

    if not args.confirm:
        print("Abortado: passe --confirm para executar a cópia.")
        return 1

    if not is_postgres_url():
        print("DATABASE_URL no .env deve apontar para Postgres.")
        return 1

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        print(f"SQLite não encontrado: {sqlite_path}")
        return 1

    sqlite_url = _sqlite_url_from_path(sqlite_path)
    if not is_sqlite_url(sqlite_url):
        print(f"URL SQLite inválida: {sqlite_url}")
        return 1

    print(f"Origem:  {sqlite_path}")
    print(f"Destino: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print("Copiando...")

    try:
        counts = copy_data(sqlite_url, settings.DATABASE_URL)
    except Exception as exc:
        print(f"Erro na cópia: {exc}")
        return 1

    total = sum(counts.values())
    n_nonzero = sum(1 for v in counts.values() if v > 0)
    print(f"Concluído: {total} linhas em {n_nonzero} tabelas.")
    print("Rode: python scripts/postgres_comparar.py")
    print("      python scripts/baseline_numeros.py comparar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
