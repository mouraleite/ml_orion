"""Cache das telas pesadas (11/11/2026)."""
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.testclient import TestClient

from app.core import cache_respostas as cr


def _montar(versao, validar=lambda t: True):
    app = FastAPI()
    contagem = {"n": 0}

    @app.get("/api/v1/dashboard/dfc/2026")
    def dfc(x: int = 0):
        contagem["n"] += 1
        return {"x": x, "chamada": contagem["n"], "texto": "a" * 3000}

    @app.get("/api/v1/outra")
    def outra():
        contagem["n"] += 1
        return {"chamada": contagem["n"]}

    @app.get("/api/v1/dashboard/dfc/erro")
    def erro():
        contagem["n"] += 1
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="não")

    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    app.add_middleware(cr.CacheRespostas, versao_dados=lambda: versao["v"], validar_token=validar)
    return TestClient(app), contagem


A = {"Authorization": "Bearer tokenA", "X-Department-Id": "18"}


def test_acerto_devolve_a_mesma_resposta_sem_recalcular():
    v = {"v": "0/1"}
    c, n = _montar(v)
    r1 = c.get("/api/v1/dashboard/dfc/2026?x=1", headers=A)
    r2 = c.get("/api/v1/dashboard/dfc/2026?x=1", headers=A)
    assert n["n"] == 1
    assert r1.content == r2.content and r2.headers["x-cache"] == "HIT" and r1.headers["x-cache"] == "MISS"
    assert r2.headers.get("content-encoding") == "gzip"


def test_gravacao_no_banco_invalida():
    v = {"v": "0/1"}
    c, n = _montar(v)
    c.get("/api/v1/dashboard/dfc/2026", headers=A)
    v["v"] = "0/2"
    r = c.get("/api/v1/dashboard/dfc/2026", headers=A)
    assert n["n"] == 2 and r.json()["chamada"] == 2


def test_cada_usuario_e_departamento_tem_o_seu():
    v = {"v": "0/1"}
    c, n = _montar(v)
    c.get("/api/v1/dashboard/dfc/2026", headers=A)
    c.get("/api/v1/dashboard/dfc/2026", headers={"Authorization": "Bearer tokenB", "X-Department-Id": "18"})
    c.get("/api/v1/dashboard/dfc/2026", headers={"Authorization": "Bearer tokenA", "X-Department-Id": "19"})
    c.get("/api/v1/dashboard/dfc/2026?x=2", headers=A)
    assert n["n"] == 4


def test_token_invalido_nao_usa_cache():
    v = {"v": "0/1"}
    c, n = _montar(v, validar=lambda t: False)
    c.get("/api/v1/dashboard/dfc/2026", headers=A)
    c.get("/api/v1/dashboard/dfc/2026", headers=A)
    assert n["n"] == 2


def test_sem_token_sem_versao_rota_fora_ou_erro_nao_guarda():
    v = {"v": "0/1"}
    c, n = _montar(v)
    c.get("/api/v1/dashboard/dfc/2026"); c.get("/api/v1/dashboard/dfc/2026")
    c.get("/api/v1/outra", headers=A); c.get("/api/v1/outra", headers=A)
    c.get("/api/v1/dashboard/dfc/erro", headers=A); c.get("/api/v1/dashboard/dfc/erro", headers=A)
    assert n["n"] == 6
    v["v"] = None
    c.get("/api/v1/dashboard/dfc/2026", headers=A); c.get("/api/v1/dashboard/dfc/2026", headers=A)
    assert n["n"] == 8


def test_limite_de_memoria(monkeypatch):
    monkeypatch.setattr(cr, "LIMITE_TOTAL", 1)
    v = {"v": "0/1"}
    c, n = _montar(v)
    c.get("/api/v1/dashboard/dfc/2026", headers=A); c.get("/api/v1/dashboard/dfc/2026", headers=A)
    assert n["n"] == 2
