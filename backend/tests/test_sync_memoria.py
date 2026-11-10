"""Sync não carrega a história inteira do CC na memória (incidente de 10/11/2026)."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services import sienge_sync as ss


def _cc(db):
    cc = CostCenter(nome="CC grande", id_sienge="12800")
    db.add(cc)
    db.flush()
    return cc


def _linha_inc(sid, valor, data="2026-11-09"):
    return {"source_id": sid, "payment_date": data, "transaction_type": "INCOME", "value": valor,
            "category_name": "Receita", "bill_id": 1, "creditor_name": "", "document_name": "", "document_number": ""}


def _historia(db, cc, n=300):
    for i in range(n):
        db.add(ActualTransaction(cost_center_id=cc.id, source_id=f"INC-H{i}", transaction_type="INCOME",
                                 transaction_date=date(2020, 1, 1), value=1.0, is_forecast=False))
    db.flush()


def test_incomes_so_carrega_os_ids_da_busca(db_session, monkeypatch):
    cc = _cc(db_session)
    _historia(db_session, cc)
    # lançamento antigo cujo source_id volta na busca (mudou a data): deve ser atualizado, não duplicado
    db_session.add(ActualTransaction(cost_center_id=cc.id, source_id="INC-X", transaction_type="INCOME",
                                     transaction_date=date(2026, 10, 1), value=5.0, is_forecast=False))
    db_session.flush()
    monkeypatch.setattr(ss, "_fetch_paginated_bulk", lambda url: iter([[{"x": 1}]]))
    import app.services.sienge_income_parse as ip
    monkeypatch.setattr(ip, "iter_income_bank_lines", lambda item, cc_id: [_linha_inc("INC-X", 7.0), _linha_inc("INC-NOVO", 3.0)])

    carregados = []
    orig = ss._existentes_por_source_id

    def espia(db, cc_id, ids, *f):
        r = orig(db, cc_id, ids, *f)
        carregados.append(len(r))
        return r

    monkeypatch.setattr(ss, "_existentes_por_source_id", espia)
    ss.sync_incomes(db_session, cc, "2026-11-07", "2026-11-09")

    assert carregados == [1]  # só o INC-X; os 300 da história não vão para a memória
    rows = {r.source_id: r for r in db_session.query(ActualTransaction).filter_by(cost_center_id=cc.id).all()}
    assert rows["INC-X"].value == 7.0 and rows["INC-X"].transaction_date == date(2026, 11, 9)
    assert rows["INC-NOVO"].value == 3.0
    assert db_session.query(ActualTransaction).filter_by(cost_center_id=cc.id, source_id="INC-X").count() == 1
    assert sum(1 for s in rows if s.startswith("INC-H")) == 300


def test_outcomes_atualiza_sem_duplicar(db_session, monkeypatch):
    cc = _cc(db_session)
    db_session.add(ActualTransaction(cost_center_id=cc.id, source_id="OUT-1-OP1-PMT-1-DT-20261001-FC-2",
                                     transaction_type="OUTCOME", transaction_date=date(2026, 10, 1), value=1.0,
                                     is_forecast=False))
    db_session.add(ActualTransaction(cost_center_id=cc.id, source_id="OUT-TARIFA-9-BM-1-FC-2",
                                     transaction_type="OUTCOME", transaction_date=date(2020, 1, 1), value=2.0,
                                     is_forecast=False))
    db_session.flush()
    monkeypatch.setattr(ss, "_fetch_paginated_bulk", lambda url: iter([[{"x": 1}]]))
    import app.services.sienge_outcome_parse as op
    linha = {"source_id": "OUT-1-OP1-PMT-1-DT-20261001-FC-2", "payment_date": "2026-11-08", "value": 9.0,
             "category_name": "Obras", "bill_id": 1, "creditor_name": "", "document_name": "",
             "document_number": "", "authorization_name": None}
    monkeypatch.setattr(op, "iter_outcome_realizado_lines", lambda item, cc_id: [linha])
    ss.sync_outcomes(db_session, cc, "2026-11-07", "2026-11-09")
    pag = db_session.query(ActualTransaction).filter_by(cost_center_id=cc.id, source_id=linha["source_id"]).all()
    assert len(pag) == 1 and pag[0].value == 9.0 and pag[0].transaction_date == date(2026, 11, 8)
    tarifa = db_session.query(ActualTransaction).filter_by(cost_center_id=cc.id, source_id="OUT-TARIFA-9-BM-1-FC-2").one()
    assert tarifa.value == 2.0  # tarifa intocada


def test_lotes_de_500(db_session):
    cc = _cc(db_session)
    _historia(db_session, cc, n=1200)
    r = ss._existentes_por_source_id(db_session, cc.id, [f"INC-H{i}" for i in range(1200)] + [None, ""])
    assert len(r) == 1200
