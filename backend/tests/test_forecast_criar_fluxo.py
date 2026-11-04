"""Criação do forecast (um documento por departamento/versão)."""
from datetime import datetime

from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.fechamento import ClosedMonth
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.user import User
from app.api.deps import get_active_department, get_current_user
from app.main import app
from app.services.budget_shared import extract_visualizacao_itens
from app.services.departamento_leitura import departamento_sentinela_todos


def _criar_orc_despesas(client, ano, produto_id=1, jan=10.0):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano, "tipo": "DESPESAS",
        "produto_id": produto_id, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    oid = r.json()["orcamento_id"]
    client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
        "itens": [{
            "produto_id": produto_id, "plano_financeiro_id": 1,
            "jan": jan, "total_anual": jan,
        }]
    })
    return oid


def test_criar_mesmo_empreendimento_no_departamento_recusa(client):
    oid = _criar_orc_despesas(client, 2070)
    r1 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2070, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2070, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r2.status_code == 400, r2.text
    assert "Já existe forecast criado" in r2.json()["detail"]


def test_criar_mesmo_empreendimento_em_outro_departamento(client, db_session):
    oid = _criar_orc_despesas(client, 2071)
    r1 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2071, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r1.status_code == 200, r1.text

    d2 = Departamento(id=2, nome="Tesouraria")
    db_session.add(d2)
    db_session.add(DepartamentoPlano(departamento_id=2, plano_financeiro_id=1, permitido=True))
    orc2 = Orcamento(
        descricao="Orçamento", ano=2071, tipo="DESPESAS", departamento_id=2,
        versao_numero=1, status="Rascunho", usuario_criador_id=1,
    )
    db_session.add(orc2)
    db_session.flush()
    db_session.add(OrcamentoItem(
        orcamento_id=orc2.id, produto_id=1, plano_financeiro_id=1, jan=40.0, total_anual=40.0,
    ))
    db_session.commit()

    def override_dept():
        return db_session.query(Departamento).filter(Departamento.id == 2).first()

    app.dependency_overrides[get_active_department] = override_dept
    try:
        r2 = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": 2071, "tipo": "DESPESAS", "produto_id": 1,
            "versao_base_orcamento_id": orc2.id,
        })
        assert r2.status_code == 200, r2.text
    finally:
        app.dependency_overrides[get_active_department] = lambda: db_session.query(Departamento).filter(Departamento.id == 1).first()

    docs = db_session.query(Forecast).filter(Forecast.ano == 2071, Forecast.tipo == "DESPESAS").all()
    assert len({d.departamento_id for d in docs}) == 2


def test_criar_copia_so_o_empreendimento_escolhido(client, db_session):
    db_session.add(ProdutoPlanoFinanceiro(produto_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2072, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    oid = r.json()["orcamento_id"]
    client.post("/api/v1/orcamentos/criar", json={
        "ano": 2072, "tipo": "DESPESAS", "produto_id": 2, "plano_financeiro_id": 1,
    })
    client.post("/api/v1/orcamentos/despesas/2072/salvar", json={
        "itens": [
            {"produto_id": 1, "plano_financeiro_id": 1, "jan": 100.0, "total_anual": 100.0},
            {"produto_id": 2, "plano_financeiro_id": 1, "jan": 40.0, "total_anual": 40.0},
        ]
    })
    r2 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2072, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r2.status_code == 200, r2.text
    fid = r2.json()["forecast_id"]
    db_session.expire_all()
    itens = db_session.query(ForecastItem).filter_by(forecast_id=fid).all()
    assert {(i.produto_id, i.jan) for i in itens} == {(1, 100.0)}
    fc = db_session.query(Forecast).filter_by(id=fid).first()
    assert fc.produto_id is None


def test_criar_nao_fecha_meses(client, db_session):
    ano = datetime.now().year
    oid = _criar_orc_despesas(client, ano)
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": ano, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r.status_code == 200, r.text
    assert db_session.query(ClosedMonth).filter_by(ano=ano).count() == 0


def test_criar_recusa_quando_forecast_fechado(client, db_session):
    oid = _criar_orc_despesas(client, 2073)
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2073, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    fid = r.json()["forecast_id"]
    client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Em aprovação"})
    client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Fechado"})
    r2 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2073, "tipo": "DESPESAS", "produto_id": 2,
        "versao_base_orcamento_id": oid, "plano_financeiro_id": 1,
    })
    assert r2.status_code == 403, r2.text


def test_incluir_segundo_empreendimento_exige_plano(client):
    r1 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2074, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2074, "tipo": "DESPESAS", "produto_id": 2,
    })
    assert r2.status_code == 400, r2.text


def test_criar_do_zero_com_plano(client, db_session):
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2075, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    fid = r.json()["forecast_id"]
    item = db_session.query(ForecastItem).filter_by(forecast_id=fid).first()
    assert item is not None
    assert item.jan == 0.0


def test_comparativo_soma_dois_departamentos(client, db_session):
    plano = db_session.query(FinancialPlan).filter_by(id=1).first()
    plano.db_id = "2.01"
    db_session.commit()
    oid = _criar_orc_despesas(client, 2076, jan=100.0)
    r1 = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2076, "tipo": "DESPESAS", "produto_id": 1,
        "versao_base_orcamento_id": oid,
    })
    assert r1.status_code == 200, r1.text
    fc1 = db_session.query(Forecast).filter_by(id=r1.json()["forecast_id"]).first()

    d2 = Departamento(id=2, nome="Tesouraria")
    db_session.add(d2)
    db_session.add(DepartamentoPlano(departamento_id=2, plano_financeiro_id=1, permitido=True))
    fc2 = Forecast(
        descricao=fc1.descricao, ano=2076, tipo="DESPESAS", departamento_id=2,
        versao_numero=1, status="Rascunho", usuario_criador_id=1, produto_id=None,
    )
    db_session.add(fc2)
    db_session.flush()
    db_session.add(ForecastItem(
        forecast_id=fc2.id, produto_id=1, plano_financeiro_id=1, jan=40.0, total_anual=40.0,
    ))
    db_session.commit()

    itens = extract_visualizacao_itens(
        db_session, 2076, "DESPESAS", departamento_sentinela_todos().id,
        f"FC_{fc1.descricao}",
    )
    linha = next(i for i in itens if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1)
    assert linha["jan"] == 140.0


def test_vendas_restrito_ao_departamento_vendas(client, db_session):
    def override_user():
        return db_session.query(User).filter(User.id == 2).first()

    app.dependency_overrides[get_current_user] = override_user
    try:
        r = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": 2077, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
        })
        assert r.status_code == 403, r.text
    finally:
        app.dependency_overrides[get_current_user] = lambda: db_session.query(User).filter(User.id == 1).first()


def test_criar_vendas_admin_ok(client, db_session):
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2078, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert r.status_code == 200, r.text
    fid = r.json()["forecast_id"]
    item = db_session.query(ForecastVendaItem).filter_by(forecast_id=fid).first()
    assert item is not None
    assert item.produto_id == 1
    assert item.ano == 2078


def test_salvar_forecast_vendas_altera_numero_com_observacao_nula(client, db_session):
    """Espelha a tela: GET devolve observacao null, usuário muda um mês e clica Salvar."""
    criar = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2080, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert criar.status_code == 200, criar.text
    loaded = client.get("/api/v1/forecasts/vendas/2080")
    assert loaded.status_code == 200, loaded.text
    itens = loaded.json()["itens"]
    assert itens, "GET deveria devolver a linha criada"
    itens[0]["observacao"] = None
    mes = itens[0]["meses"][0]
    mes["numero_vendas"] = 3
    mes["ticket_medio"] = 180000.0
    mes["vgv"] = 540000.0
    resp = client.post("/api/v1/forecasts/vendas/2080/salvar", json={"itens": itens})
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    fid = criar.json()["forecast_id"]
    gravado = db_session.query(ForecastVendaItem).filter_by(
        forecast_id=fid, mes=mes["mes"],
    ).first()
    assert gravado is not None
    assert gravado.numero_vendas == 3
    assert gravado.ticket_medio == 180000.0
    assert gravado.vgv == 540000.0


def test_salvar_inclui_empreendimento_novo_no_mesmo_documento(client, db_session):
    db_session.add(ProdutoPlanoFinanceiro(produto_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2079, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    fid = r.json()["forecast_id"]
    r2 = client.post("/api/v1/forecasts/despesas/2079/salvar", json={
        "itens": [
            {"produto_id": 1, "plano_financeiro_id": 1, "jan": 10.0, "total_anual": 10.0},
            {"produto_id": 2, "plano_financeiro_id": 1, "jan": 5.0, "total_anual": 5.0},
        ]
    })
    assert r2.status_code == 200, r2.text
    db_session.expire_all()
    pids = {
        i.produto_id
        for i in db_session.query(ForecastItem).filter_by(forecast_id=fid).all()
    }
    assert pids == {1, 2}
    assert db_session.query(Forecast).filter_by(ano=2079, tipo="DESPESAS").count() == 1
