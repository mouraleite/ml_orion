"""Carga 2026 de contas a pagar (com autorização) + conferência por departamento."""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import distinct, extract, text

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from app.db.database import SessionLocal, is_sqlite_url
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.user import User
from app.services.departamento_leitura import (
    departamento_id_realizado,
    departamento_sentinela_todos,
)
from app.services.realizado_sienge import source_id_realizado_despesa
from app.services.sienge_sync import sync_outcomes

START = "2026-01-01"
END = date.today().isoformat()
ANO = 2026


def _session():
    db = SessionLocal()
    if is_sqlite_url():
        db.execute(text("PRAGMA busy_timeout=120000"))
    return db


def ccs_com_out(db) -> list[CostCenter]:
    ids = [
        row[0]
        for row in db.query(distinct(ActualTransaction.cost_center_id))
        .filter(
            ActualTransaction.source_id.like("OUT-%"),
            extract("year", ActualTransaction.transaction_date) == ANO,
            ActualTransaction.is_forecast == False,  # noqa: E712
        )
        .all()
        if row[0] is not None
    ]
    return (
        db.query(CostCenter)
        .filter(CostCenter.id.in_(ids), CostCenter.id_sienge.isnot(None))
        .order_by(CostCenter.id_sienge)
        .all()
    )


def resync_outcomes() -> tuple[int, int]:
    db = _session()
    ok = fail = 0
    try:
        ccs = ccs_com_out(db)
        print(f"Resync OUT {START}..{END} — {len(ccs)} CCs", flush=True)
        for i, cc in enumerate(ccs, 1):
            for attempt in range(1, 4):
                try:
                    sync_outcomes(db, cc, START, END)
                    ok += 1
                    print(f"  [{i}/{len(ccs)}] OK {cc.id_sienge} {str(cc.nome)[:40]}", flush=True)
                    break
                except Exception as e:
                    db.rollback()
                    msg = str(e).split("\n")[0]
                    if "database is locked" in msg.lower() and attempt < 3:
                        time.sleep(3 * attempt)
                        continue
                    fail += 1
                    print(f"  [{i}/{len(ccs)}] ERRO {cc.id_sienge}: {msg}", flush=True)
                    break
        print(f"Carga concluida: ok={ok} fail={fail}", flush=True)
        return ok, fail
    finally:
        db.close()


def cobertura_nomes(db) -> None:
    q = db.query(ActualTransaction).filter(
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast == False,  # noqa: E712
        extract("year", ActualTransaction.transaction_date) == ANO,
        ActualTransaction.source_id.like("OUT-%"),
    )
    rows = [r for r in q.all() if source_id_realizado_despesa(r.source_id)]
    named = sum(1 for r in rows if (r.authorization_name or "").strip())
    print(f"Parcelas OUT {ANO} (premissas tela): {len(rows)} | com name: {named} | sem name: {len(rows) - named}", flush=True)
    por_nome: dict[str, int] = defaultdict(int)
    for r in rows:
        por_nome[(r.authorization_name or "").strip() or "(sem name)"] += 1
    print("  nomes Sienge:", flush=True)
    for nome, n in sorted(por_nome.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {nome:32} {n:6}", flush=True)


def conferencia() -> None:
    from app.api.routes.acompanhamento import get_acompanhamento_despesas

    db = _session()
    try:
        cobertura_nomes(db)
        q = db.query(ActualTransaction).filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,  # noqa: E712
            extract("year", ActualTransaction.transaction_date) == ANO,
            ActualTransaction.source_id.like("OUT-%"),
        )
        por_dept: dict[str, float] = defaultdict(float)
        bruto = 0.0
        for r in q.all():
            if not source_id_realizado_despesa(r.source_id):
                continue
            val = float(r.value or 0)
            bruto += val
            did = departamento_id_realizado(db, r.authorization_name)
            por_dept[str(did)] += val

        depts = {d.id: d.nome for d in db.query(Departamento).all()}
        print("\n=== Realizado despesas 2026 (parcela × de-para) ===", flush=True)
        soma = 0.0
        for did, nome in sorted(depts.items(), key=lambda x: x[1].lower()):
            v = round(por_dept.get(str(did), 0.0), 2)
            if v:
                print(f"  {nome:32} {v:>16,.2f}", flush=True)
                soma += v
        print(f"  {'SOMA depts':32} {round(soma, 2):>16,.2f}", flush=True)
        print(f"  {'TOTAL parcelas':32} {round(bruto, 2):>16,.2f}", flush=True)
        print(f"  fecha soma=total? {abs(soma - bruto) < 0.05}", flush=True)

        user = db.query(User).filter(User.role.in_(["Administrador", "ADMIN"])).first()
        tes = db.query(Departamento).filter(Departamento.id == 6).first()
        ctrl = db.query(Departamento).filter(Departamento.id == 3).first()
        corp = db.query(Departamento).filter(Departamento.id == 18).first()

        def tot(data, campo):
            return round(sum((i.get(campo) or {}).get("total") or 0 for i in data.get("itens") or []), 2)

        print("\n=== Tela acompanhamento despesas 2026 ===", flush=True)
        for nome, dept in [
            ("Tesouraria", tes),
            ("Controladoria", ctrl),
            ("Corporativo", corp),
            ("Todos", departamento_sentinela_todos()),
        ]:
            d = get_acompanhamento_despesas(ANO, False, False, db, dept, user)
            print(
                f"  {nome:16} itens={len(d.get('itens') or []):4} "
                f"orcado={tot(d, 'orcado'):,.2f} realizado={tot(d, 'realizado'):,.2f}",
                flush=True,
            )
    finally:
        db.close()


def main() -> None:
    resync_outcomes()
    conferencia()


if __name__ == "__main__":
    main()
