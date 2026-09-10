"""Geração em lote de Forecast para empreendimentos sem forecast."""

from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem


def _orcamento_fechado(db, ano: int, produto_id: int = 1, com_item: bool = True) -> Orcamento:
    orc = Orcamento(
        ano=ano,
        tipo="DESPESAS",
        departamento_id=1,
        status="Fechado",
        versao_numero=1,
        descricao=f"Orçamento {ano}",
        produto_id=produto_id,
    )
    db.add(orc)
    db.flush()
    if com_item:
        db.add(OrcamentoItem(
            orcamento_id=orc.id,
            produto_id=produto_id,
            plano_financeiro_id=1,
            jan=10.0,
            total_anual=10.0,
        ))
    db.commit()
    return orc


def test_lote_cria_quem_ainda_nao_tem(client, db_session):
    _orcamento_fechado(db_session, 2050)
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2050, "tipo": "DESPESAS"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert len(corpo["criados"]) == 1
    assert corpo["criados"][0]["produto_id"] == 1
    assert corpo["criados"][0]["produto_nome"] == "Produto A"
    assert corpo["ignorados_ja_existentes"] == []
    fc = db_session.query(Forecast).filter_by(ano=2050, produto_id=1).first()
    assert fc is not None
    assert fc.status == "Rascunho"
    assert db_session.query(ForecastItem).filter_by(forecast_id=fc.id).count() == 1


def test_lote_nao_recria_quem_ja_esta_fechado(client, db_session):
    _orcamento_fechado(db_session, 2051)
    db_session.add(Forecast(
        ano=2051,
        tipo="DESPESAS",
        departamento_id=1,
        status="Fechado",
        versao_numero=1,
        descricao="Forecast - 0+12",
        produto_id=1,
    ))
    db_session.commit()
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2051, "tipo": "DESPESAS"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["criados"] == []
    assert 1 in resposta.json()["ignorados_ja_existentes"]
    assert db_session.query(Forecast).filter_by(ano=2051).count() == 1


def test_lote_cria_orcamento_sem_itens_pelo_produto_id(client, db_session):
    _orcamento_fechado(db_session, 2052, com_item=False)
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2052, "tipo": "DESPESAS"})
    assert resposta.status_code == 200, resposta.text
    assert len(resposta.json()["criados"]) == 1
    fc = db_session.query(Forecast).filter_by(ano=2052, produto_id=1).first()
    assert fc is not None
    assert db_session.query(ForecastItem).filter_by(forecast_id=fc.id).count() == 0


def _orcamento_vendas_fechado(db, ano: int, produto_id: int = 1, com_item: bool = True) -> Orcamento:
    orc = Orcamento(
        ano=ano,
        tipo="VENDAS",
        departamento_id=1,
        status="Fechado",
        versao_numero=1,
        descricao=f"Orçamento Vendas {ano}",
        produto_id=produto_id,
    )
    db.add(orc)
    db.flush()
    if com_item:
        db.add(OrcamentoVendaItem(
            orcamento_id=orc.id,
            produto_id=produto_id,
            plano_venda_id=1,
            mes=1,
            ticket_medio=100000.0,
            numero_vendas=2,
            vgv=200000.0,
        ))
    db.commit()
    return orc


def test_lote_vendas_cria_quem_ainda_nao_tem(client, db_session):
    _orcamento_vendas_fechado(db_session, 2060)
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2060, "tipo": "VENDAS"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert len(corpo["criados"]) == 1
    assert corpo["criados"][0]["produto_id"] == 1
    assert corpo["criados"][0]["produto_nome"] == "Produto A"
    assert corpo["ignorados_ja_existentes"] == []
    fc = db_session.query(Forecast).filter_by(ano=2060, tipo="VENDAS", produto_id=1).first()
    assert fc is not None
    assert fc.status == "Rascunho"
    itens = db_session.query(ForecastVendaItem).filter_by(forecast_id=fc.id).all()
    assert len(itens) == 1
    assert itens[0].vgv == 200000.0
    assert itens[0].numero_vendas == 2
    assert itens[0].ano == 2060


def test_lote_vendas_nao_recria_quem_ja_esta_fechado(client, db_session):
    _orcamento_vendas_fechado(db_session, 2061)
    db_session.add(Forecast(
        ano=2061,
        tipo="VENDAS",
        departamento_id=1,
        status="Fechado",
        versao_numero=1,
        descricao="Forecast - 0+12",
        produto_id=1,
    ))
    db_session.commit()
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2061, "tipo": "VENDAS"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["criados"] == []
    assert 1 in resposta.json()["ignorados_ja_existentes"]
    assert db_session.query(Forecast).filter_by(ano=2061, tipo="VENDAS").count() == 1


def test_lote_vendas_cria_orcamento_sem_itens_pelo_produto_id(client, db_session):
    _orcamento_vendas_fechado(db_session, 2062, com_item=False)
    resposta = client.post("/api/v1/forecasts/gerar-lote", json={"ano": 2062, "tipo": "VENDAS"})
    assert resposta.status_code == 200, resposta.text
    assert len(resposta.json()["criados"]) == 1
    fc = db_session.query(Forecast).filter_by(ano=2062, tipo="VENDAS", produto_id=1).first()
    assert fc is not None
    assert db_session.query(ForecastVendaItem).filter_by(forecast_id=fc.id).count() == 0
