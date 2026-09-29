"""Cota e log das chamadas deste ERP ao Sienge."""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.sienge_api_call import SiengeApiCall
from app.services.sienge_client import SiengeClient
from app.services.sienge_usage import (
    BULK_DAILY_LIMIT,
    REST_DAILY_LIMIT,
    build_month_report,
    classify_sienge_family,
    counts_toward_quota,
    record_sienge_http_call,
    safe_request_path,
)


def test_classify_rest_vs_bulk_pela_url():
    rest = "https://api.sienge.com.br/mouraleite/public/api/v1/customers"
    bulk = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/outcome"
    assert classify_sienge_family(rest) == "REST"
    assert classify_sienge_family(bulk) == "BULK"
    assert "/public/api/" in bulk
    assert classify_sienge_family(bulk) != "REST"


def test_caminho_sem_query_nem_credencial():
    url = "https://user:secret@api.sienge.com.br/mouraleite/public/api/v1/customers?token=abc&offset=1"
    path = safe_request_path(url)
    assert path == "/mouraleite/public/api/v1/customers"
    assert "secret" not in path
    assert "token" not in path


def test_401_e_5xx_fora_da_cota_429_e_200_dentro():
    assert counts_toward_quota(200) is True
    assert counts_toward_quota(429) is True
    assert counts_toward_quota(404) is True
    assert counts_toward_quota(401) is False
    assert counts_toward_quota(500) is False
    assert counts_toward_quota(503) is False
    assert counts_toward_quota(None) is False


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _session():
    engine = _engine()
    SiengeApiCall.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_agregado_mensal_exclui_401_e_5xx_e_limita_endpoints():
    db = _session()
    setembro = datetime(2026, 9, 1, 15, 0, 0)
    outro_dia = datetime(2026, 9, 2, 15, 0, 0)
    agosto_no_fuso = datetime(2026, 9, 1, 2, 0, 0)
    rows = [
        SiengeApiCall(created_at=setembro, family="REST", method="GET", path="/mouraleite/public/api/v1/a", status_code=200, duration_ms=10),
        SiengeApiCall(created_at=setembro, family="REST", method="GET", path="/mouraleite/public/api/v1/a", status_code=429, duration_ms=10),
        SiengeApiCall(created_at=setembro, family="REST", method="GET", path="/mouraleite/public/api/v1/a", status_code=401, duration_ms=10),
        SiengeApiCall(created_at=setembro, family="REST", method="GET", path="/mouraleite/public/api/v1/a", status_code=500, duration_ms=10),
        SiengeApiCall(created_at=outro_dia, family="BULK", method="GET", path="/mouraleite/public/api/bulk-data/v1/outcome", status_code=200, duration_ms=10),
        SiengeApiCall(created_at=outro_dia, family="BULK", method="GET", path="/mouraleite/public/api/bulk-data/v1/outcome", status_code=503, duration_ms=10),
        SiengeApiCall(created_at=agosto_no_fuso, family="REST", method="GET", path="/mouraleite/public/api/v1/agosto", status_code=200, duration_ms=10),
    ]
    for i in range(16):
        rows.append(
            SiengeApiCall(
                created_at=setembro,
                family="REST",
                method="GET",
                path=f"/mouraleite/public/api/v1/ep/{i:02d}",
                status_code=200,
                duration_ms=1,
            )
        )
    db.add_all(rows)
    db.commit()

    report = build_month_report(db, 2026, 9, today=date(2026, 9, 15))
    rest = next(item for item in report["familias"] if item["familia"] == "REST")
    bulk = next(item for item in report["familias"] if item["familia"] == "BULK")

    assert report["historico_vazio"] is False
    assert rest["limite_diario"] == REST_DAILY_LIMIT
    assert bulk["limite_diario"] == BULK_DAILY_LIMIT
    # 200 + 429 + 16 endpoints. 401, 500 e o dia 31/08 (fuso SP) ficam de fora.
    assert rest["total"] == 18
    assert rest["http_429"] == 1
    assert rest["http_401"] == 1
    assert rest["http_5xx"] == 1
    assert rest["maior_dia"] == "2026-09-01"
    assert rest["maior_dia_total"] == 18
    assert bulk["total"] == 1
    assert bulk["http_5xx"] == 1
    assert bulk["http_429"] == 0
    assert len(report["endpoints"]) == 15
    assert report["endpoints"][0]["quantidade"] >= report["endpoints"][-1]["quantidade"]
    assert all(item["quantidade"] > 0 for item in report["endpoints"])
    dia1 = next(dia for dia in rest["dias"] if dia["data"] == "2026-09-01")
    assert dia1["medido"] is True
    assert dia1["acima_do_limite"] is False
    assert dia1["total"] == 18


def test_historico_vazio_nao_inventa_totais():
    db = _session()
    report = build_month_report(db, 2026, 9)
    assert report["historico_vazio"] is True
    assert report["endpoints"] == []
    assert report["familias"][0]["total"] is None


def test_falha_ao_gravar_log_nao_propaga(monkeypatch):
    monkeypatch.setattr("app.db.database.SessionLocal", MagicMock(side_effect=RuntimeError("db fora")))
    record_sienge_http_call(
        url="https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/outcome",
        method="GET",
        status_code=200,
        duration_ms=8,
    )

    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    payload = {"results": [{"id": 1}]}

    def fake_urlopen(req, timeout=30):
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("app.services.sienge_usage.record_sienge_http_call", side_effect=RuntimeError("db fora")):
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert client.get_json("https://api.sienge.com.br/mouraleite/public/api/v1/customers") == payload


def test_get_json_registra_status_http():
    import urllib.error

    client = SiengeClient(subdomain="mouraleite", user="u", password="p")
    captured = []

    def capture(**kwargs):
        captured.append(kwargs)

    def fake_urlopen(req, timeout=30):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

    with patch("app.services.sienge_usage.record_sienge_http_call", side_effect=capture):
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert client.get_json("https://api.sienge.com.br/mouraleite/public/api/v1/b", retries=1) is None

    assert captured[0]["status_code"] == 429
    assert captured[0]["url"].startswith("https://api.sienge.com.br/")


def test_dia_acima_do_limite(monkeypatch):
    from app.services import sienge_usage

    db = _session()
    db.add(
        SiengeApiCall(
            created_at=datetime(2026, 9, 3, 15, 0, 0),
            family="REST",
            method="GET",
            path="/mouraleite/public/api/v1/estouro",
            status_code=200,
            duration_ms=1,
        )
    )
    db.commit()
    monkeypatch.setitem(sienge_usage._LIMITS, "REST", (0, 200))
    report = sienge_usage.build_month_report(db, 2026, 9, today=date(2026, 9, 15))
    rest = next(item for item in report["familias"] if item["familia"] == "REST")
    dia = next(item for item in rest["dias"] if item["data"] == "2026-09-03")
    assert dia["acima_do_limite"] is True
    assert rest["limite_diario"] == 0


def test_record_grava_familia_e_path(monkeypatch):
    engine = _engine()
    SiengeApiCall.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr("app.db.database.SessionLocal", Session)
    record_sienge_http_call(
        url="https://user:secret@api.sienge.com.br/mouraleite/public/api/bulk-data/v1/outcome?token=abc",
        method="GET",
        status_code=429,
        duration_ms=4,
    )
    row = Session().query(SiengeApiCall).one()
    assert row.family == "BULK"
    assert row.path == "/mouraleite/public/api/bulk-data/v1/outcome"
    assert row.status_code == 429
    assert "secret" not in row.path
    assert "token" not in row.path
