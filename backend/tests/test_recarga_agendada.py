"""Recarga agendada: o sync diário usa a data de system_settings uma vez e apaga a chave."""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core import scheduler as sch
from app.models.system_settings import SystemSettings


def _agendar(db, valor):
    db.add(SystemSettings(key=sch.CHAVE_RECARGA, value=valor))
    db.flush()


def test_sem_chave_nao_ha_recarga(db_session):
    assert sch.recarga_pendente(db_session) is None


def test_data_valida_e_lida_e_apagada(db_session):
    d = (date.today() - timedelta(days=60)).isoformat()
    _agendar(db_session, {"desde": d})
    assert sch.recarga_pendente(db_session) == d
    sch.limpar_recarga_pendente(db_session)
    assert sch.recarga_pendente(db_session) is None


def test_data_fora_da_faixa_e_ignorada(db_session):
    _agendar(db_session, {"desde": "2001-01-01"})
    assert sch.recarga_pendente(db_session) is None


def test_financeiro_usa_a_data_e_limpa(db_session, monkeypatch):
    d = (date.today() - timedelta(days=30)).isoformat()
    _agendar(db_session, {"desde": d})
    chamadas = []
    monkeypatch.setattr(sch, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    for nome in ("run_sync_empresas", "run_sync_centros_custo", "run_sync_planos_financeiros", "run_sync_departamentos_sienge"):
        monkeypatch.setattr(sch, nome, lambda db: 0)
    monkeypatch.setattr(sch, "sync_all_sienge_data", lambda db, full_load=False, desde=None: chamadas.append(desde))
    sch._executar_sync_diario()
    assert chamadas == [d]
    assert sch.recarga_pendente(db_session) is None
