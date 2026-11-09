"""Fase 1, passo 3 (09/11/2026): o sync nunca apaga dados com base em leitura parcial do Sienge."""
import os
import sys
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import Base, load_models
load_models()
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services import sienge_client, sienge_sync
from app.services.sienge_client import SiengeClient, SiengeFetchError


class _ClienteQueFalha(SiengeClient):
    """Primeira página volta cheia; a segunda falha (get_json -> None, como em timeout/HTTP 5xx)."""

    def __init__(self, paginas_ok=1):
        super().__init__("x", "u", "p")
        self.chamadas = 0
        self.paginas_ok = paginas_ok

    def get_json(self, url, **kw):
        self.chamadas += 1
        if self.chamadas <= self.paginas_ok:
            return {"data": [{"id": f"item-{self.chamadas}"}] * 200}
        return None


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False)()
    s.add(CostCenter(id=1, nome="CC Teste", id_sienge="99901"))
    s.commit()
    yield s
    s.close()


def _usar_cliente(monkeypatch, cliente):
    monkeypatch.setattr(sienge_sync, "get_default_client", lambda: cliente)
    monkeypatch.setattr(sienge_client, "_safe_record_sienge_call", lambda *a, **k: None)
    monkeypatch.setattr(sienge_client.time, "sleep", lambda s: None)


def _linhas(db, prefixo):
    return db.query(ActualTransaction).filter(ActualTransaction.source_id.like(prefixo + "%")).count()


# --- cliente -----------------------------------------------------------------

def test_paginacao_estrita_avisa_quando_o_sienge_falha(monkeypatch):
    monkeypatch.setattr(sienge_client, "_safe_record_sienge_call", lambda *a, **k: None)
    cli = _ClienteQueFalha(paginas_ok=1)
    paginas = []
    with pytest.raises(SiengeFetchError):
        for p in cli.paginate_bulk("https://x/outcome?a=1", strict=True):
            paginas.append(p)
    assert len(paginas) == 1


def test_paginacao_padrao_continua_igual_para_quem_nao_pediu_estrito(monkeypatch):
    monkeypatch.setattr(sienge_client, "_safe_record_sienge_call", lambda *a, **k: None)
    paginas = list(_ClienteQueFalha(paginas_ok=1).paginate_bulk("https://x/outcome?a=1"))
    assert len(paginas) == 1


def test_estrito_tenta_3_vezes_antes_de_desistir(monkeypatch):
    monkeypatch.setattr(sienge_client, "_safe_record_sienge_call", lambda *a, **k: None)
    tentativas = []

    class Cli(SiengeClient):
        def get_json(self, url, **kw):
            tentativas.append(kw.get("retries"))
            return None

    with pytest.raises(SiengeFetchError):
        list(Cli("x", "u", "p").paginate_bulk("https://x/o?a=1", strict=True))
    assert tentativas == [3]


# --- realizado: pagamentos e recebimentos --------------------------------------

def test_falha_no_sienge_nao_apaga_pagamentos_realizados(db, monkeypatch):
    hoje = date.today()
    db.add(ActualTransaction(cost_center_id=1, source_id="OUT-1-OP1-PMT-1-DT-x-FC-1", transaction_type="OUTCOME",
                             transaction_date=hoje, value=1000.0, category="Obras", is_forecast=False))
    db.commit()
    _usar_cliente(monkeypatch, _ClienteQueFalha(paginas_ok=0))
    ini = (hoje - timedelta(days=3)).isoformat()
    with pytest.raises(SiengeFetchError):
        sienge_sync.sync_outcomes(db, db.get(CostCenter, 1), ini, hoje.isoformat())
    db.rollback()
    assert _linhas(db, "OUT-1-OP1") == 1


def test_falha_no_sienge_nao_apaga_recebimentos_realizados(db, monkeypatch):
    hoje = date.today()
    db.add(ActualTransaction(cost_center_id=1, source_id="INC-1-1", transaction_type="INCOME",
                             transaction_date=hoje, value=500.0, category="Receita", is_forecast=False))
    db.commit()
    _usar_cliente(monkeypatch, _ClienteQueFalha(paginas_ok=0))
    ini = (hoje - timedelta(days=3)).isoformat()
    with pytest.raises(SiengeFetchError):
        sienge_sync.sync_incomes(db, db.get(CostCenter, 1), ini, hoje.isoformat())
    db.rollback()
    assert _linhas(db, "INC-1") == 1


# --- previsões e vencidos -------------------------------------------------------

@pytest.mark.parametrize("func,tipo,sid", [
    ("sync_payables_forecast", "OUTCOME", "FCST-OUT-9-1"),
    ("sync_receivables_forecast", "INCOME", "FCST-INC-9-1"),
])
def test_falha_no_sienge_nao_apaga_previsoes(db, monkeypatch, func, tipo, sid):
    db.add(ActualTransaction(cost_center_id=1, source_id=sid, transaction_type=tipo,
                             transaction_date=date.today() + timedelta(days=30), value=900.0,
                             category="X", is_forecast=True))
    db.commit()
    _usar_cliente(monkeypatch, _ClienteQueFalha(paginas_ok=0))
    with pytest.raises(SiengeFetchError):
        getattr(sienge_sync, func)(db, db.get(CostCenter, 1))
    db.rollback()
    assert _linhas(db, sid) == 1


def test_falha_no_sienge_nao_apaga_titulos_vencidos(db, monkeypatch):
    db.add(ActualTransaction(cost_center_id=1, source_id="TRK-VENC-INC-1", transaction_type="INCOME",
                             transaction_date=date.today() - timedelta(days=10), value=300.0,
                             category="X", is_forecast=True))
    db.commit()
    _usar_cliente(monkeypatch, _ClienteQueFalha(paginas_ok=0))
    with pytest.raises(SiengeFetchError):
        sienge_sync.sync_overdue_open_tracking(db, db.get(CostCenter, 1))
    db.rollback()
    assert _linhas(db, "TRK-VENC") == 1


def test_previsao_e_trocada_quando_a_busca_termina(db, monkeypatch):
    """Caminho feliz: Sienge responde (vazio) -> previsão antiga sai, nada quebra."""
    db.add(ActualTransaction(cost_center_id=1, source_id="FCST-OUT-9-1", transaction_type="OUTCOME",
                             transaction_date=date.today() + timedelta(days=30), value=900.0,
                             category="X", is_forecast=True))
    db.commit()

    class Vazio(SiengeClient):
        def get_json(self, url, **kw):
            return {"data": []}

    _usar_cliente(monkeypatch, Vazio("x", "u", "p"))
    sienge_sync.sync_payables_forecast(db, db.get(CostCenter, 1))
    assert _linhas(db, "FCST-OUT-9-1") == 0


def test_sync_geral_registra_o_cc_que_falhou_e_nao_grava_data_de_sync(db, monkeypatch):
    db.get(CostCenter, 1).track_in_dashboard = True
    db.commit()
    _usar_cliente(monkeypatch, _ClienteQueFalha(paginas_ok=0))
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: None)
    monkeypatch.setattr(sienge_sync, "sync_bank_movements_batch", lambda *a, **k: None)
    monkeypatch.setattr(sienge_sync, "sync_sienge_colaboradores", lambda db: None)
    import app.services.tracking_engineering as eng
    import app.services.sienge_account_balances as saldos
    monkeypatch.setattr(eng, "sync_engineering_disbursements", lambda db: {})
    monkeypatch.setattr(saldos, "persist_closed_year_balances", lambda db: {})
    with pytest.raises(RuntimeError, match="99901"):
        sienge_sync.sync_all_sienge_data(db, full_load=False)
