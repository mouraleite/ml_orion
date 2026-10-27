"""
Regrava PMT legado (OUT-{titulo}-PMT-n) com financialCategoryRate × valor do título.

Só o acompanhamento lê esse source_id. Não chama sync_outcomes (isso gravaria OP1
e o orçamento passaria a ver o histórico).
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from app.db.database import SessionLocal
from app.services.sienge_sync import rewrite_pmt_historico_todos_ccs

START_YEAR = 2016
END_YEAR = 2026


def main() -> None:
    db = SessionLocal()
    try:
        tot = rewrite_pmt_historico_todos_ccs(db, START_YEAR, END_YEAR)
        print(f"Concluido: {tot}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
