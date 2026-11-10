"""Testes unitários do cliente Sienge unificado (Onda 5)."""

import json
from unittest.mock import MagicMock, patch

from app.services.sienge_client import (
    SiengeClient,
    api_v1_base_url,
    build_auth_header,
    bulk_base_url,
)


def test_build_auth_header_basic():
    headers = build_auth_header("user", "pass")
    assert headers["Authorization"].startswith("Basic ")
    assert "user:pass" in __import__("base64").b64decode(headers["Authorization"].split()[1]).decode()


def test_base_urls():
    assert bulk_base_url("mouraleite").endswith("/mouraleite/public/api/bulk-data/v1")
    assert api_v1_base_url("mouraleite").endswith("/mouraleite/public/api/v1")


def test_paginate_bulk_yields_pages():
    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    page1 = {"data": [{"id": 1, "billId": 10, "installmentId": 1}]}
    page2 = {"data": []}

    def fake_urlopen(req, timeout=30):
        url = req.full_url
        if "offset=0" in url:
            body = json.dumps(page1).encode()
        else:
            body = json.dumps(page2).encode()
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        pages = list(client.paginate_bulk("https://example.com/outcome?startDate=2026-01-01"))

    assert len(pages) == 1
    assert pages[0][0]["id"] == 1


def test_paginate_v1_collect():
    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    payload = {
        "results": [{"departmentId": 1, "departmentName": "Fin"}],
        "resultSetMetadata": {"count": 1},
    }

    def fake_urlopen(req, timeout=30):
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        rows = client.paginate_v1_collect("https://example.com/departments")

    assert len(rows) == 1
    assert rows[0]["departmentName"] == "Fin"


def test_paginate_v1_aceita_lista_sem_envelope():
    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    payload = [{"id": 2030409, "name": "Conceituação", "tpConta": "R"}]

    def fake_urlopen(req, timeout=30):
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        pages = list(client.paginate_v1_pages("https://example.com/payment-categories"))

    assert len(pages) == 1
    assert pages[0][0]["id"] == 2030409


def test_get_json_404_returns_none_when_allowed():
    client = SiengeClient(subdomain="mouraleite", user="u", password="p")

    def fake_urlopen(req, timeout=30):
        raise __import__("urllib.error").HTTPError(req.full_url, 404, "Not Found", {}, None)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert client.get_json("https://example.com/missing", retries=1, not_found_ok=True) is None


def test_from_auth_string():
    client = SiengeClient.from_auth_string("mouraleite", "user:secret")
    assert client.user == "user"
    assert client.password == "secret"


def test_paginate_bulk_nao_repete_quando_o_sienge_ignora_o_limite():
    """Sonda de 10/11/2026: limit=5 trouxe 12.709 itens. Página maior que o limite = resposta completa."""
    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    chamadas = []

    class Cli(SiengeClient):
        def get_json(self, url, **kw):
            chamadas.append(url)
            return {"data": [{"id": i} for i in range(250)]}

    pages = list(Cli("mouraleite", "u", "p").paginate_bulk("https://example.com/outcome?a=1", limit=200))
    assert len(chamadas) == 1
    assert len(pages) == 1 and len(pages[0]) == 250
