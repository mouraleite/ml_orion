"""Fase 1 (09/11/2026): rotas protegidas e trava única do sync Sienge."""
import os
import sys
import threading

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.api import deps
from app.api.routes import sync as sync_routes
from app.core import scheduler
from app.models.user import User


def _user(role: str) -> User:
    u = User(id=7, email="t@test.com", full_name="T", role=role, hashed_password="x")
    u.is_active = True
    return u


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _como(role):
    app.dependency_overrides[deps.get_current_user] = lambda: _user(role)


# --- rotas sem login -------------------------------------------------------

@pytest.mark.parametrize("metodo,rota", [
    ("post", "/api/v1/migration/run"),
    ("post", "/api/v1/migration/run-forecast"),
    ("post", "/api/v1/sync/sienge"),
])
def test_rotas_exigem_login(client, metodo, rota):
    r = getattr(client, metodo)(rota)
    assert r.status_code in (401, 403), r.text


def test_debug_143_nao_existe_mais(client):
    r = client.get("/api/v1/tracking/debug_143")
    assert r.status_code != 200


def test_sync_status_continua_publico_para_o_github_actions(client):
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200


# --- migração: só administrador -------------------------------------------

def test_migracao_recusa_usuario_comum(client):
    _como("Usuário Comum")
    assert client.post("/api/v1/migration/run").status_code == 403
    assert client.post("/api/v1/migration/run-forecast").status_code == 403


def test_migracao_aceita_administrador(client, monkeypatch):
    import app.api.routes.migration as mig
    chamadas = []
    monkeypatch.setattr(mig, "_run_migration_task", lambda: chamadas.append(1))
    _como("Administrador")
    assert client.post("/api/v1/migration/run").status_code == 200
    assert chamadas == [1]


# --- sync manual: incremental liberado, carga completa só admin -----------

def test_sync_incremental_liberado_para_usuario(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sync_routes, "_run_sienge_sync_job", lambda full: chamadas.append(full))
    _como("Usuário Comum")
    r = client.post("/api/v1/sync/sienge")
    assert r.status_code == 200 and chamadas == [False]


def test_sync_carga_completa_recusa_usuario(client, monkeypatch):
    monkeypatch.setattr(sync_routes, "_run_sienge_sync_job", lambda full: None)
    _como("Usuário Comum")
    assert client.post("/api/v1/sync/sienge?full_load=true").status_code == 403


def test_sync_carga_completa_aceita_admin(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sync_routes, "_run_sienge_sync_job", lambda full: chamadas.append(full))
    _como("Administrador")
    assert client.post("/api/v1/sync/sienge?full_load=true").status_code == 200
    assert chamadas == [True]


# --- trava única ----------------------------------------------------------

def test_dois_syncs_nao_rodam_juntos():
    dentro = threading.Event()
    liberar = threading.Event()
    resultado = {}

    def lento():
        dentro.set()
        liberar.wait(5)

    t = threading.Thread(target=lambda: resultado.setdefault("1", scheduler.run_with_sync_lock(lento, "A")))
    t.start()
    assert dentro.wait(5)
    segundo = scheduler.run_with_sync_lock(lambda: None, "B")
    liberar.set()
    t.join(5)
    assert segundo is False
    assert resultado["1"] is True
    # depois de terminar, a trava é liberada
    assert scheduler.run_with_sync_lock(lambda: None, "C") is True


def test_trava_liberada_mesmo_com_erro():
    with pytest.raises(RuntimeError):
        scheduler.run_with_sync_lock(lambda: (_ for _ in ()).throw(RuntimeError("x")), "erro")
    assert scheduler.run_with_sync_lock(lambda: None, "depois") is True


def test_sync_manual_usa_a_trava(monkeypatch):
    usados = []
    monkeypatch.setattr(scheduler, "run_with_sync_lock", lambda fn, nome: usados.append(nome) or True)
    sync_routes._run_sienge_sync_job(False)
    assert usados == ["Sync manual"]


def test_sync_diario_respeita_sync_manual_em_andamento(monkeypatch):
    rodou = []
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: rodou.append(1))
    lock = scheduler._hold_sync_lock()
    try:
        scheduler.daily_sienge_sync()
    finally:
        scheduler._release_sync_lock(lock)
    assert rodou == []


def test_testes_nao_ligam_o_agendador(monkeypatch):
    """Subir a API nos testes não pode disparar sync real, nem na janela das 9h/14h."""
    disparos = []
    monkeypatch.setattr(scheduler, "na_janela_do_sync", lambda: True)
    monkeypatch.setattr(scheduler, "daily_sienge_sync", lambda: disparos.append(1))
    monkeypatch.setattr(scheduler.scheduler, "start", lambda: disparos.append("start"))
    assert os.environ.get("ERP_ML_DISABLE_SCHEDULER") == "1"
    scheduler.start_scheduler()
    assert disparos == []
