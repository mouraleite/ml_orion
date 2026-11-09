"""Sync no Render gratuito: keep-alive durante o sync e tentativas repetidas sem refazer trabalho."""
import os
import sys
import threading
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.api.routes import sync as sync_routes
from app.core import scheduler, sync_keepalive
from app.core.config import settings


class _Setting:
    def __init__(self, value):
        self.value = value


class _Query:
    def __init__(self, setting):
        self._s = setting

    def filter_by(self, **_):
        return self

    def first(self):
        return self._s


class _DB:
    def __init__(self, ts):
        self._s = _Setting({"timestamp": ts}) if ts else None

    def query(self, *_):
        return _Query(self._s)

    def close(self):
        pass


AGORA = datetime(2026, 11, 9, 12, 0, 0)


# --- sync_concluido_recentemente ------------------------------------------

@pytest.mark.parametrize("ts,esperado", [
    (None, False),
    ("2026-11-09T11:00:00", True),     # 1h atrás
    ("2026-11-09T10:00:01", True),     # pouco menos de 2h
    ("2026-11-09T09:59:00", False),    # mais de 2h
    ("2026-11-08T11:30:00", False),    # ontem
    ("2026-11-09T13:00:00", False),    # no futuro: relógio estranho, não pula
    ("lixo", False),
])
def test_sync_concluido_recentemente(ts, esperado):
    assert scheduler.sync_concluido_recentemente(_DB(ts), agora=AGORA) is esperado


# --- daily_sienge_sync -----------------------------------------------------

@pytest.fixture
def sem_sync_real(monkeypatch):
    chamadas = []
    monkeypatch.setattr(scheduler, "_executar_sync_diario", lambda: chamadas.append(1))
    return chamadas


def test_daily_pula_quando_sync_recente(monkeypatch, sem_sync_real):
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: True)
    assert scheduler.daily_sienge_sync() == "recente"
    assert sem_sync_real == []
    # a trava foi devolvida: a próxima chamada consegue rodar
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: False)
    assert scheduler.daily_sienge_sync() == "executado"
    assert len(sem_sync_real) == 1


def test_daily_sem_checagem_roda_mesmo_com_sync_recente(monkeypatch, sem_sync_real):
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: True)
    assert scheduler.daily_sienge_sync(pular_se_recente=False) == "executado"
    assert len(sem_sync_real) == 1


def test_daily_ignora_quando_ja_ha_sync_rodando(monkeypatch, sem_sync_real):
    monkeypatch.setattr(scheduler, "_hold_sync_lock", lambda: False)
    assert scheduler.daily_sienge_sync() == "em_execucao"
    assert sem_sync_real == []


def test_daily_libera_a_trava_mesmo_se_o_sync_falhar(monkeypatch):
    def _quebra():
        raise RuntimeError("Sienge fora")

    monkeypatch.setattr(scheduler, "_executar_sync_diario", _quebra)
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: False)
    with pytest.raises(RuntimeError):
        scheduler.daily_sienge_sync()
    monkeypatch.setattr(scheduler, "_executar_sync_diario", lambda: None)
    assert scheduler.daily_sienge_sync() == "executado"


def test_daily_liga_keep_alive_durante_o_sync(monkeypatch):
    estado = {}

    class _KA:
        def __enter__(self):
            estado["ligado"] = True

        def __exit__(self, *a):
            estado["ligado"] = False

    monkeypatch.setattr(scheduler, "manter_acordado", lambda: _KA())
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: False)
    monkeypatch.setattr(
        scheduler, "_executar_sync_diario", lambda: estado.setdefault("durante", estado["ligado"])
    )
    scheduler.daily_sienge_sync()
    assert estado["durante"] is True
    assert estado["ligado"] is False


# --- POST /sync/cron ---------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "s3")
    disparos = []
    monkeypatch.setattr(sync_routes, "daily_sienge_sync", lambda: disparos.append(1))
    c = TestClient(app)
    c.disparos = disparos
    return c


def test_cron_nao_dispara_se_sync_recente(client, monkeypatch):
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: True)
    r = client.post("/api/v1/sync/cron", headers={"X-Cron-Secret": "s3"})
    assert r.status_code == 200
    assert r.json()["iniciado"] is False
    assert client.disparos == []


def test_cron_dispara_quando_nao_ha_sync_recente(client, monkeypatch):
    monkeypatch.setattr(scheduler, "sync_concluido_recentemente", lambda db: False)
    r = client.post("/api/v1/sync/cron", headers={"X-Cron-Secret": "s3"})
    assert r.status_code == 200
    assert r.json()["iniciado"] is True
    assert client.disparos == [1]


def test_cron_continua_exigindo_segredo(client):
    assert client.post("/api/v1/sync/cron", headers={"X-Cron-Secret": "errado"}).status_code == 401


# --- keep-alive --------------------------------------------------------------

def test_keep_alive_desligado_fora_do_render(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    with sync_keepalive.manter_acordado(intervalo=0.01) as ligado:
        assert ligado is False


def test_keep_alive_chama_health_enquanto_ativo_e_para_depois(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://api.exemplo.com/")
    urls = []
    monkeypatch.setattr(sync_keepalive.httpx, "get", lambda url, timeout: urls.append(url))
    with sync_keepalive.manter_acordado(intervalo=0.02) as ligado:
        assert ligado is True
        time.sleep(0.15)
    n = len(urls)
    assert n >= 2
    assert set(urls) == {"https://api.exemplo.com/health"}
    time.sleep(0.1)
    assert len(urls) == n
    assert not [t for t in threading.enumerate() if t.name == "sync-keepalive"]


def test_keep_alive_sobrevive_a_erro_de_rede(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://api.exemplo.com")
    tentativas = []

    def _falha(url, timeout):
        tentativas.append(url)
        raise RuntimeError("rede caiu")

    monkeypatch.setattr(sync_keepalive.httpx, "get", _falha)
    with sync_keepalive.manter_acordado(intervalo=0.02):
        time.sleep(0.12)
    assert len(tentativas) >= 2
