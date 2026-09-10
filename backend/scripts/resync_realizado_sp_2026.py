"""
Resync realizado Sienge (outcome + income + bank-movement) para CCs com SP-MIG 2026.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from sqlalchemy import distinct, extract

from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services.sienge_sync import (
    mirror_afac_income_as_outcome,
    sync_bank_movements_batch,
    sync_incomes,
    sync_outcomes,
)

START = "2026-01-01"
END = "2026-08-31"
ANO = 2026


def cc_ids_com_sp_mig(db) -> list[CostCenter]:
    ids = (
        db.query(distinct(ActualTransaction.cost_center_id))
        .filter(
            ActualTransaction.source_id.like("SP-MIG-%"),
            extract("year", ActualTransaction.transaction_date) == ANO,
        )
        .all()
    )
    cc_pks = [row[0] for row in ids if row[0] is not None]
    return (
        db.query(CostCenter)
        .filter(CostCenter.id.in_(cc_pks))
        .order_by(CostCenter.id_sienge)
        .all()
    )


def main() -> None:
    db = SessionLocal()
    try:
        ccs = cc_ids_com_sp_mig(db)
        print(f"Resync {START}..{END} — {len(ccs)} CCs com SP-MIG {ANO}")
        ok = fail = 0
        for i, cc in enumerate(ccs, 1):
            if not cc.id_sienge:
                continue
            print(f"[{i}/{len(ccs)}] {cc.id_sienge} {cc.nome[:40]}")
            try:
                sync_outcomes(db, cc, START, END)
                sync_incomes(db, cc, START, END)
                mirror_afac_income_as_outcome(db, cc, START, END)
                ok += 1
            except Exception as e:
                fail += 1
                print(f"  ERRO: {e}")
        print("Bank-movement batch (todos CCs)...")
        try:
            sync_bank_movements_batch(db, START, END, cost_centers=ccs)
            print("Bank-movement OK")
        except Exception as e:
            fail += 1
            print(f"Bank-movement ERRO: {e}")
        print(f"Concluido: ok={ok} fail={fail}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
