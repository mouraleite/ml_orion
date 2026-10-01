"""GET/SAVE do Forecast de Receitas: linhas auto das vendas não são sobrescritas."""
from app.models.forecast import Forecast, ForecastItem


def test_get_receitas_vazio_quando_nao_existe(client):
    resp = client.get("/api/v1/forecasts/receitas/2090")
    assert resp.status_code == 200, resp.text
    assert resp.json().get("is_empty") is True


def test_criar_e_salvar_receitas_preserva_linha_auto(client, db_session):
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2091, "tipo": "RECEITAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    fid = r.json()["forecast_id"]
    db_session.expire_all()
    item = db_session.query(ForecastItem).filter_by(forecast_id=fid).one()
    item.jan = 100.0
    item.total_anual = 100.0
    item.is_auto_generated = True
    db_session.commit()

    visao = client.get("/api/v1/forecasts/receitas/2091")
    assert visao.status_code == 200, visao.text
    body = visao.json()
    assert body["forecast_id"] == fid
    auto = next(i for i in body["itens"] if i["produto_id"] == 1)
    assert auto["is_auto_generated"] is True
    assert auto["jan"] == 100.0

    salvo = client.post("/api/v1/forecasts/receitas/2091/salvar", json={
        "itens": [{
            "produto_id": 1, "plano_financeiro_id": 1,
            "jan": 1.0, "total_anual": 1.0,
        }],
    })
    assert salvo.status_code == 200, salvo.text
    db_session.expire_all()
    kept = db_session.query(ForecastItem).filter_by(forecast_id=fid).one()
    assert kept.is_auto_generated is True
    assert kept.jan == 100.0

    visao2 = client.get("/api/v1/forecasts/receitas/2091")
    auto2 = next(i for i in visao2.json()["itens"] if i["produto_id"] == 1)
    assert auto2["jan"] == 100.0
