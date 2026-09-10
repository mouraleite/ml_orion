"""
Compara contagens de linhas: SQLite (origem) vs Postgres (.env).

Uso:

  python scripts/postgres_comparar.py
  python scripts/postgres_comparar.py --sqlite ./viabilidades.db
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from app.db.database import is_postgres_url, load_models


def _counts(engine) -> dict[str, int]:
    insp = inspect(engine)
    out = {}
    for name in sorted(insp.get_table_names()):
        if name == "alembic_version":
            continue
        with engine.connect() as conn:
            n = conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0
        out[name] = int(n)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sqlite",
        default=str(Path(__file__).resolve().parents[1] / "viabilidades.db"),
    )
    args = parser.parse_args()

    if not is_postgres_url():
        print("DATABASE_URL no .env deve ser Postgres para comparar.")
        return 1

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        print(f"SQLite não encontrado: {sqlite_path}")
        return 1

    load_models()
    sqlite_engine = create_engine(
        f"sqlite:///{sqlite_path.resolve().as_posix()}",
        connect_args={"check_same_thread": False},
    )
    pg_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    src = _counts(sqlite_engine)
    dst = _counts(pg_engine)

    all_tables = sorted(set(src) | set(dst))
    diffs = []
    for t in all_tables:
        a, b = src.get(t, 0), dst.get(t, 0)
        if a != b:
            diffs.append(f"  {t}: sqlite={a} postgres={b}")

    if diffs:
        print("Divergências encontradas:")
        print("\n".join(diffs[:50]))
        if len(diffs) > 50:
            print(f"  ... e mais {len(diffs) - 50}")
        return 1

    total = sum(dst.values())
    print(f"OK: {len(all_tables)} tabelas, {total} linhas — contagens iguais ao SQLite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
