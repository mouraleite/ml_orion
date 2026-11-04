"""Criação e salvamento do orçamento (documento por departamento)."""
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.financial_plan import FinancialPlan
from app.models.cost_center import CostCenter
from app.api.deps import get_active_department
from app.main import app
from app.services.departamento_leitura import departamento_sentinela_todos


def test_criar_mesmo_empreendimento_no_departamento_recusa(client):
    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2045, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2045, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r2.status_code == 400
    assert "Já existe orçamento criado" in r2.json()["detail"]


def test_criar_mesmo_empreendimento_em_outro_departamento(client, db_session):
    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2046, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text

    d2 = Departamento(id=2, nome="Tesouraria")
    db_session.add(d2)
    db_session.add(DepartamentoPlano(departamento_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()

    def override_dept():
        return db_session.query(Departamento).filter(Departamento.id == 2).first()

    app.dependency_overrides[get_active_department] = override_dept
    try:
        r2 = client.post("/api/v1/orcamentos/criar", json={
            "ano": 2046, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
        })
        assert r2.status_code == 200, r2.text
    finally:
        app.dependency_overrides[get_active_department] = lambda: db_session.query(Departamento).filter(Departamento.id == 1).first()

    docs = db_session.query(Orcamento).filter(Orcamento.ano == 2046, Orcamento.tipo == "DESPESAS").all()
    assert len({d.departamento_id for d in docs}) == 2


def test_salvar_receitas_nao_grava_em_outro_departamento(client, db_session):
    client.post("/api/v1/orcamentos/criar", json={
        "ano": 2047, "tipo": "RECEITAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    d2 = Departamento(id=2, nome="Tesouraria")
    db_session.add(d2)
    db_session.commit()
    alien = Orcamento(
        descricao="Orçamento", ano=2047, tipo="RECEITAS", departamento_id=2,
        versao_numero=1, status="Rascunho", usuario_criador_id=1,
    )
    db_session.add(alien)
    db_session.flush()
    db_session.add(OrcamentoItem(
        orcamento_id=alien.id, produto_id=1, plano_financeiro_id=1, jan=50.0, total_anual=50.0,
    ))
    db_session.commit()
    alien_id = alien.id

    resp = client.post("/api/v1/orcamentos/receitas/2047/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 10.0, "total_anual": 10.0}],
    })
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    outro = db_session.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == alien_id).first()
    assert outro is not None
    assert outro.jan == 50.0


def test_salvar_recusa_linha_repetida(client):
    client.post("/api/v1/orcamentos/criar", json={
        "ano": 2048, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    resp = client.post("/api/v1/orcamentos/despesas/2048/salvar", json={
        "itens": [
            {"produto_id": 1, "plano_financeiro_id": 1, "jan": 1.0, "total_anual": 1.0},
            {"produto_id": 1, "plano_financeiro_id": 1, "fev": 2.0, "total_anual": 2.0},
        ],
    })
    assert resp.status_code == 400


def test_salvar_despesas_com_matriz_produto_vazia(client, db_session):
    """Produção: produto_plano_financeiro está vazio; a carga Excel já ignora isso."""
    client.post("/api/v1/orcamentos/criar", json={
        "ano": 2061, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    db_session.query(ProdutoPlanoFinanceiro).delete()
    db_session.commit()
    resp = client.post("/api/v1/orcamentos/despesas/2061/salvar", json={
        "itens": [{
            "produto_id": 1,
            "plano_financeiro_id": 1,
            "jan": 9000.0,
            "set": 9000.0,
            "total_anual": 18000.0,
            "observacao": None,
        }],
    })
    assert resp.status_code == 200, resp.text


def test_excel_recusa_orcamento_aprovado(client, db_session):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2049, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    oid = r.json()["orcamento_id"]
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Em aprovação"})
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Fechado"})
    resp = client.post(
        "/api/v1/orcamentos/excel/importar/DESPESAS/2049",
        files={"file": ("planilha.xlsx", b"not-xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 403


def test_documento_unico_chamado_orcamento(client, db_session):
    client.post("/api/v1/orcamentos/criar", json={
        "ano": 2050, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    orc = db_session.query(Orcamento).filter_by(ano=2050, tipo="DESPESAS").one()
    assert orc.descricao == "Orçamento"
    assert orc.produto_id is None
    assert db_session.query(OrcamentoItem).filter_by(orcamento_id=orc.id).count() == 1


def test_catalogo_despesas_com_db_id(client, db_session):
    from app.models.financial_plan import FinancialPlan
    from app.models.cost_center import CostCenter

    plano = db_session.query(FinancialPlan).filter_by(id=1).one()
    plano.db_id = "2.01"
    plano.tp_conta = "R"
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.status = "Ativo"
    db_session.commit()

    r = client.get("/api/v1/orcamentos/catalogo?tipo=DESPESAS")
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(p["id"] == 1 for p in body["opcoes_produtos"])
    assert any(p["id"] == 1 for p in body["opcoes_planos"])


def test_criar_vendas_mesmo_empreendimento_recusa(client):
    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2051, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2051, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert r2.status_code == 400
    assert "Já existe orçamento criado" in r2.json()["detail"]


def test_salvar_vendas_altera_numero_com_observacao_nula(client, db_session):
    """Espelha a tela: GET devolve observacao null, usuário muda um mês e clica Salvar."""
    from app.models.orcamento import Orcamento, OrcamentoVendaItem

    criar = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2062, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert criar.status_code == 200, criar.text
    loaded = client.get("/api/v1/orcamentos/vendas/2062")
    assert loaded.status_code == 200, loaded.text
    itens = loaded.json()["itens"]
    assert itens, "GET deveria devolver a linha criada"
    itens[0]["observacao"] = None
    mes = itens[0]["meses"][0]
    mes["numero_vendas"] = 4
    mes["ticket_medio"] = 250000.0
    mes["vgv"] = 1000000.0
    resp = client.post("/api/v1/orcamentos/vendas/2062/salvar", json={"itens": itens})
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    orc = db_session.query(Orcamento).filter_by(ano=2062, tipo="VENDAS").first()
    gravado = db_session.query(OrcamentoVendaItem).filter_by(
        orcamento_id=orc.id, mes=mes["mes"],
    ).first()
    assert gravado is not None
    assert gravado.numero_vendas == 4
    assert gravado.ticket_medio == 250000.0
    assert gravado.vgv == 1000000.0


def test_salvar_vendas_permite_venda_e_distrato_mesmo_plano(client):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2052, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
    })
    assert r.status_code == 200, r.text
    resp = client.post("/api/v1/orcamentos/vendas/2052/salvar", json={
        "itens": [
            {
                "produto_id": 1, "plano_venda_id": 1, "observacao": "",
                "meses": [{"mes": 1, "ticket_medio": 10, "numero_vendas": 1, "vgv": 10}],
            },
            {
                "produto_id": 1, "plano_venda_id": 1, "observacao": "(Distrato)",
                "meses": [{"mes": 1, "ticket_medio": 10, "numero_vendas": -1, "vgv": -10}],
            },
        ],
    })
    assert resp.status_code == 200, resp.text


def test_criar_receitas_mesmo_empreendimento_recusa(client):
    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2053, "tipo": "RECEITAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2053, "tipo": "RECEITAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r2.status_code == 400
    assert "Já existe orçamento criado" in r2.json()["detail"]


def test_criar_mesmo_empreendimento_em_outro_ano_permite(client):
    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2054, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2055, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r2.status_code == 200, r2.text


def test_criar_recusa_quando_orcamento_fechado(client, db_session):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2056, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    oid = r.json()["orcamento_id"]
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Em aprovação"})
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Fechado"})
    r2 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2056, "tipo": "DESPESAS", "produto_id": 2, "plano_financeiro_id": 1,
    })
    assert r2.status_code == 403
    assert "fechado" in r2.json()["detail"].lower() or "aprovação" in r2.json()["detail"].lower()


def test_salvar_recusa_quando_orcamento_fechado(client):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2057, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    oid = r.json()["orcamento_id"]
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Em aprovação"})
    client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Fechado"})
    resp = client.post("/api/v1/orcamentos/despesas/2057/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 99.0, "total_anual": 99.0}],
    })
    assert resp.status_code == 403


def test_vendas_recusa_departamento_que_nao_e_vendas(client, db_session):
    from app.api.deps import get_current_user
    from app.models.user import User

    app.dependency_overrides[get_current_user] = lambda: db_session.query(User).filter(User.id == 2).first()
    try:
        r = client.post("/api/v1/orcamentos/criar", json={
            "ano": 2058, "tipo": "VENDAS", "produto_id": 1, "plano_venda_id": 1,
        })
        assert r.status_code == 403
        assert "Vendas" in r.json()["detail"]
    finally:
        app.dependency_overrides[get_current_user] = lambda: db_session.query(User).filter(User.id == 1).first()


def test_visualizacao_soma_mesmo_par_em_dois_departamentos(client, db_session):
    plano = db_session.query(FinancialPlan).filter_by(id=1).one()
    plano.db_id = "2.01"
    plano.tp_conta = "R"
    db_session.query(CostCenter).filter_by(id=1).update({"status": "Ativo"})
    d2 = Departamento(id=2, nome="Tesouraria")
    db_session.add(d2)
    db_session.add(DepartamentoPlano(departamento_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()

    r1 = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2060, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r1.status_code == 200, r1.text
    client.post("/api/v1/orcamentos/despesas/2060/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 100.0, "total_anual": 100.0}],
    })

    def override_dept2():
        return db_session.query(Departamento).filter(Departamento.id == 2).first()

    app.dependency_overrides[get_active_department] = override_dept2
    try:
        r2 = client.post("/api/v1/orcamentos/criar", json={
            "ano": 2060, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
        })
        assert r2.status_code == 200, r2.text
        s2 = client.post("/api/v1/orcamentos/despesas/2060/salvar", json={
            "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 40.0, "total_anual": 40.0}],
        })
        assert s2.status_code == 200, s2.text
    finally:
        app.dependency_overrides[get_active_department] = lambda: db_session.query(Departamento).filter(Departamento.id == 1).first()

    app.dependency_overrides[get_active_department] = lambda: departamento_sentinela_todos()
    try:
        vis = client.get("/api/v1/orcamentos/visualizacao/2060?tipo=DESPESAS&versao_id=OC_Orçamento")
        assert vis.status_code == 200, vis.text
        itens = vis.json()["itens"]
        par = next(i for i in itens if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1)
        assert par["jan"] == 140.0

        comp = client.get(
            "/api/v1/orcamentos/comparativo"
            "?versao_a=OC_Orçamento&versao_b=OC_Orçamento&tipo=DESPESAS&ano=2060"
        )
        assert comp.status_code == 200, comp.text
        body = comp.json()
        inclusoes = body.get("inclusoes") or []
        exclusoes = body.get("exclusoes") or []
        alteracoes = body.get("alteracoes") or []
        assert inclusoes == [] and exclusoes == []
        if alteracoes:
            mesmo = next((x for x in alteracoes if x.get("produto_id") == 1), None)
            if mesmo:
                assert (mesmo.get("versao_a") or {}).get("jan") == 140.0
    finally:
        app.dependency_overrides[get_active_department] = lambda: db_session.query(Departamento).filter(Departamento.id == 1).first()
