"""Respostas JSON rápidas: mesmo resultado do FastAPI (11/11/2026)."""
import datetime as dt
import enum
import json
import uuid
from decimal import Decimal

import pytest
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from app.core.resposta_rapida import RespostaJSON, gerar_json


def _antigo(conteudo) -> bytes:
    return json.dumps(
        jsonable_encoder(conteudo), ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")
    ).encode("utf-8")


class Cor(enum.Enum):
    AZUL = "azul"


class Modelo(BaseModel):
    nome: str
    quando: dt.date


class ObjetoQualquer:
    def __init__(self):
        self.a = 1
        self.b = dt.date(2026, 1, 2)


CASOS = [
    {"a": 1.5, "b": [1, None, "x"], 3: {"d": dt.date(2026, 11, 11)}, "e": Decimal("2.50"), "f": Decimal("3")},
    [{"quando": dt.datetime(2026, 1, 1, 10, 30), "id": uuid.UUID(int=5), "cor": Cor.AZUL}],
    {"modelo": Modelo(nome="Órion", quando=dt.date(2026, 2, 3)), "t": (1, 2), "vazio": {}},
    {"obj": ObjetoQualquer()},  # tipo desconhecido → caminho antigo
    {Cor.AZUL: 1},  # chave que não é texto → caminho antigo
    {"bool": True, "none": None, "neg": -0.0, "grande": 1e300, "texto": "ação \"aspas\" \n"},
]


@pytest.mark.parametrize("conteudo", CASOS)
def test_bytes_iguais_ao_caminho_antigo(conteudo):
    try:
        esperado = _antigo(conteudo)
    except Exception as e:  # noqa: BLE001
        with pytest.raises(type(e)):
            gerar_json(conteudo)
        return
    assert gerar_json(conteudo) == esperado


def test_gerador_vai_pelo_caminho_antigo():
    assert gerar_json({"g": (i for i in range(3))}) == _antigo({"g": (i for i in range(3))})


def test_nan_continua_recusado():
    with pytest.raises(ValueError):
        gerar_json({"x": float("nan")})


def test_resposta_json_usa_o_mesmo_gerador():
    assert RespostaJSON({"n": "Órion"}).body == _antigo({"n": "Órion"})


def test_rota_sem_modelo_e_com_modelo(client):
    # sem response_model (dict) e com response_model continuam iguais ao FastAPI
    r = client.get("/openapi.json")
    assert r.status_code == 200 and r.json()["openapi"]


def test_gzip_em_resposta_grande(client):
    r = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_rota_fastapi_isolada():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.resposta_rapida import instalar

    instalar()
    app = FastAPI()

    @app.get("/d")
    def d():
        return {"data": dt.date(2026, 1, 1), "v": Decimal("1.25"), "obj": ObjetoQualquer()}

    @app.get("/m", response_model=Modelo)
    def m():
        return {"nome": "x", "quando": "2026-01-01", "extra": 1}

    @app.get("/s", status_code=201)
    def s():
        return [1, 2]

    c = TestClient(app)
    assert c.get("/d").content == _antigo({"data": dt.date(2026, 1, 1), "v": Decimal("1.25"), "obj": ObjetoQualquer()})
    assert c.get("/m").json() == {"nome": "x", "quando": "2026-01-01"}
    r = c.get("/s")
    assert r.status_code == 201 and r.json() == [1, 2]
