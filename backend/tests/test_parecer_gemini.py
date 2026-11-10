"""Parecer por IA (Gemini): chave do servidor, sem pedir na tela; lib carregada só na hora."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_sem_chave_avisa_com_codigo(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app.models.viability import Viability
    r = client.post("/api/v1/viabilities/999999/generate-summary", json={})
    assert r.status_code == 404  # viabilidade inexistente vem antes


def test_sem_chave_em_viabilidade_existente(client, db_session, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app.models.viability import Viability
    v = Viability(project_name="Teste IA")
    db_session.add(v)
    db_session.flush()
    r = client.post(f"/api/v1/viabilities/{v.id}/generate-summary", json={})
    assert r.status_code == 400 and r.json()["detail"].startswith("GEMINI_SEM_CHAVE")


def test_biblioteca_nao_e_carregada_na_subida():
    import app.api.routes.viabilities as rv
    assert not hasattr(rv, "genai")
