"""Reabertura de forecast fechado: mesmo id, cópia Substituído, acompanhamento congelado."""
from app.models.forecast import Forecast, ForecastItem


def _fechar_forecast_despesas(client, ano: int, jan: float = 100.0) -> int:
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    oid = r.json()["orcamento_id"]
    assert client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": jan, "total_anual": jan}],
    }).status_code == 200
    criado = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": ano, "tipo": "DESPESAS", "produto_id": 1, "versao_base_orcamento_id": oid,
    })
    assert criado.status_code == 200, criado.text
    fid = criado.json()["forecast_id"]
    assert client.post(f"/api/v1/forecasts/despesas/{ano}/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": jan, "total_anual": jan}],
    }).status_code == 200
    assert client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Em aprovação"}).status_code == 200
    fechado = client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Fechado"})
    assert fechado.status_code == 200, fechado.text
    return fid


def _forecast_jan(client, ano: int) -> float:
    resp = client.get(f"/api/v1/acompanhamento/despesas/{ano}")
    assert resp.status_code == 200, resp.text
    item = next(
        i for i in resp.json()["itens"]
        if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
    )
    return item["forecast"]["jan"]


def test_acompanhamento_forecast_nao_muda_ao_solicitar(client, db_session):
    fid = _fechar_forecast_despesas(client, 2082, jan=100.0)
    assert _forecast_jan(client, 2082) == 100.0
    r = client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "Ajuste pontual"},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    fc = db_session.query(Forecast).filter_by(id=fid).one()
    assert fc.status == "Solicitação Reabertura"
    assert fc.motivo_reabertura == "Ajuste pontual"
    assert _forecast_jan(client, 2082) == 100.0


def test_solicitar_reabertura_forecast_exige_motivo(client):
    fid = _fechar_forecast_despesas(client, 2083)
    r = client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "   "},
    )
    assert r.status_code == 400


def test_solicitar_reabertura_forecast_recusa_rascunho(client):
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2084, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    fid = r.json()["forecast_id"]
    resp = client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "cedo demais"},
    )
    assert resp.status_code == 400


def test_salvar_forecast_bloqueado_durante_solicitacao(client):
    fid = _fechar_forecast_despesas(client, 2085, jan=40.0)
    assert client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "bloqueio"},
    ).status_code == 200
    salvo = client.post("/api/v1/forecasts/despesas/2085/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 1.0, "total_anual": 1.0}],
    })
    assert salvo.status_code == 403


def test_recusar_reabertura_forecast_volta_fechado(client, db_session):
    fid = _fechar_forecast_despesas(client, 2086, jan=70.0)
    assert client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "pedido"},
    ).status_code == 200
    recusa = client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Fechado"})
    assert recusa.status_code == 200, recusa.text
    db_session.expire_all()
    fc = db_session.query(Forecast).filter_by(id=fid).one()
    assert fc.status == "Fechado"
    assert fc.motivo_reabertura is None
    assert _forecast_jan(client, 2086) == 70.0


def test_aprovar_reabertura_forecast_mesmo_id_acompanhamento_congelado(client, db_session):
    fid = _fechar_forecast_despesas(client, 2087, jan=100.0)
    assert client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "corrigir janeiro"},
    ).status_code == 200
    r = client.post(f"/api/v1/forecasts/{fid}/aprovar-reabertura")
    assert r.status_code == 200, r.text
    db_session.expire_all()
    live = db_session.query(Forecast).filter_by(id=fid).one()
    assert live.status == "Reaberto"
    snap = db_session.query(Forecast).filter_by(ano=2087, status="Substituído").one()
    assert snap.id != fid
    assert snap.versao_base_forecast_id == fid
    assert db_session.query(ForecastItem).filter_by(forecast_id=snap.id).one().jan == 100.0

    visao = client.get("/api/v1/forecasts/despesas/2087")
    assert visao.status_code == 200, visao.text
    assert visao.json()["forecast_id"] == fid
    assert visao.json()["status"] == "Reaberto"

    salvo = client.post("/api/v1/forecasts/despesas/2087/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 1.0, "total_anual": 1.0}],
    })
    assert salvo.status_code == 200, salvo.text
    db_session.expire_all()
    assert db_session.query(ForecastItem).filter_by(forecast_id=fid).one().jan == 1.0
    assert db_session.query(ForecastItem).filter_by(forecast_id=snap.id).one().jan == 100.0
    assert _forecast_jan(client, 2087) == 100.0


def test_status_nao_aprova_reabertura_forecast_sem_snapshot(client, db_session):
    fid = _fechar_forecast_despesas(client, 2088, jan=100.0)
    assert client.post(
        f"/api/v1/forecasts/{fid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "não pular cópia"},
    ).status_code == 200
    bypass = client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Reaberto"})
    assert bypass.status_code == 400
    db_session.expire_all()
    live = db_session.query(Forecast).filter_by(id=fid).one()
    assert live.status == "Solicitação Reabertura"
    assert db_session.query(Forecast).filter_by(ano=2088, status="Substituído").count() == 0
    assert _forecast_jan(client, 2088) == 100.0
