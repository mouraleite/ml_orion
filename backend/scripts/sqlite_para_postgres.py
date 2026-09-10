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


def _sanitize_pg_value(value: object) -> object:
    """Postgres JSON rejeita Infinity/NaN; SQLite às vezes guarda isso em texto/float."""
    import math

    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return None
    if isinstance(value, dict):
        return {k: _sanitize_pg_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_pg_value(v) for v in value]
    if isinstance(value, str) and ("Infinity" in value or "NaN" in value):
        return (
            value.replace("-Infinity", "null")
            .replace("Infinity", "null")
            .replace("NaN", "null")
        )
    return value


def _drop_foreign_keys(pg_engine) -> list[tuple[str, str]]:
    """Remove FKs (Neon não permite session_replication_role). Retorna (table, conname)."""
    dropped: list[tuple[str, str]] = []
    with pg_engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.conrelid::regclass::text AS table_name, c.conname
                FROM pg_constraint c
                JOIN pg_namespace n ON n.oid = c.connamespace
                WHERE c.contype = 'f' AND n.nspname = 'public'
                ORDER BY c.conname
                """
            )
        ).all()
        for table_name, conname in rows:
            conn.execute(text(f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS "{conname}"'))
            dropped.append((table_name, conname))
    return dropped


def _delete_orphan_produto_plano(pg_engine) -> int:
    with pg_engine.begin() as conn:
        result = conn.execute(
            text(
                """
                DELETE FROM produto_plano_financeiro ppf
                WHERE NOT EXISTS (
                    SELECT 1 FROM cost_centers cc WHERE cc.id = ppf.produto_id
                )
                OR NOT EXISTS (
                    SELECT 1 FROM planos_financeiros pf WHERE pf.id = ppf.plano_financeiro_id
                )
                """
            )
        )
        return result.rowcount or 0


def _recreate_foreign_keys(pg_engine, tables) -> None:
    from sqlalchemy.schema import AddConstraint

    for table in tables:
        for fk in table.foreign_key_constraints:
            try:
                with pg_engine.begin() as conn:
                    conn.execute(AddConstraint(fk))
            except Exception as exc:
                msg = str(exc).split("\n")[0]
                print(f"  aviso FK {table.name}.{fk.name}: {msg}", flush=True)


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

    dropped = _drop_foreign_keys(pg_engine)
    print(f"FKs temporariamente removidas: {len(dropped)}", flush=True)

    sqlite_insp = inspect(sqlite_engine)
    with sqlite_engine.connect() as src, pg_engine.begin() as dst:
        for table in tables:
            if not sqlite_insp.has_table(table.name):
                counts[table.name] = 0
                continue
            # Só colunas que existem no SQLite (modelo pode estar à frente do .db local).
            src_col_names = {c["name"] for c in sqlite_insp.get_columns(table.name)}
            cols = [c for c in table.c if c.name in src_col_names]
            if not cols:
                counts[table.name] = 0
                continue
            rows = src.execute(select(*cols)).mappings().all()
            counts[table.name] = len(rows)
            print(f"  {table.name}: {len(rows)} linhas", flush=True)
            if rows:
                payload = [
                    {k: _sanitize_pg_value(v) for k, v in dict(r).items()}
                    for r in rows
                ]
                dst.execute(table.insert(), payload)

    orphan_ppf = _delete_orphan_produto_plano(pg_engine)
    if orphan_ppf:
        print(f"Removidas {orphan_ppf} linhas órfãs em produto_plano_financeiro", flush=True)
    _recreate_foreign_keys(pg_engine, tables)
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
