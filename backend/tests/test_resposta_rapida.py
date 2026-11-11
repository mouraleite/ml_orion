"""Resposta rápida e compressão (11/11/2026)."""
import datetime as dt
import json
from decimal import Decimal

from fastapi.encoders import jsonable_encoder

from app.core.resposta_rapida import RespostaJSON


def test_mesmo_resultado_que_o_fastapi():
    dados = {"a": 1.5, "b": [1, None, "x"], 3: {"d": dt.date(2026, 11, 11)}, "e": Decimal("2.50"), "f": {1, 2}}
    rapido = json.loads(RespostaJSON(dados).body)
    padrao = json.loads(json.dumps(jsonable_encoder(dados)))
    rapido["f"] = sorted(rapido["f"]); padrao["f"] = sorted(padrao["f"])
    assert rapido == padrao


def test_acentos_sem_escape():
    assert "Órion".encode("utf-8") in RespostaJSON({"n": "Órion"}).body


def test_gzip_em_resposta_grande(client):
    r = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"
