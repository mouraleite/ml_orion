"""Reabertura de orçamento fechado: solicitar e recusar sem alterar o acompanhamento."""
from app.models.orcamento import Orcamento, OrcamentoItem


def _fechar_despesas(client, ano: int, jan: float = 100.0) -> int:
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    oid = r.json()["orcamento_id"]
    salvo = client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": jan, "total_anual": jan}],
    })
    assert salvo.status_code == 200, salvo.text
    assert client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Em aprovação"}).status_code == 200
    fechado = client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Fechado"})
    assert fechado.status_code == 200, fechado.text
    return oid


def _orcado_jan(client, ano: int) -> float:
    resp = client.get(f"/api/v1/acompanhamento/despesas/{ano}")
    assert resp.status_code == 200, resp.text
    item = next(
        i for i in resp.json()["itens"]
        if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
    )
    return item["orcado"]["jan"]


def test_acompanhamento_orcado_nao_muda_ao_solicitar(client, db_session):
    oid = _fechar_despesas(client, 2092, jan=100.0)
    antes = _orcado_jan(client, 2092)
    assert antes == 100.0

    r = client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "Ajuste pontual"},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    orc = db_session.query(Orcamento).filter_by(id=oid).one()
    assert orc.status == "Solicitação Reabertura"
    assert orc.motivo_reabertura == "Ajuste pontual"
    assert _orcado_jan(client, 2092) == 100.0
    assert db_session.query(OrcamentoItem).filter_by(orcamento_id=oid).one().jan == 100.0


def test_solicitar_reabertura_exige_motivo(client):
    oid = _fechar_despesas(client, 2093)
    r = client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "   "},
    )
    assert r.status_code == 400


def test_solicitar_reabertura_recusa_rascunho(client):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": 2094, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    oid = r.json()["orcamento_id"]
    resp = client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "cedo demais"},
    )
    assert resp.status_code == 400


def test_salvar_bloqueado_durante_solicitacao(client):
    oid = _fechar_despesas(client, 2095, jan=40.0)
    assert client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "bloqueio"},
    ).status_code == 200
    salvo = client.post("/api/v1/orcamentos/despesas/2095/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 1.0, "total_anual": 1.0}],
    })
    assert salvo.status_code == 403


def test_recusar_reabertura_volta_fechado(client, db_session):
    oid = _fechar_despesas(client, 2096, jan=70.0)
    assert client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "pedido"},
    ).status_code == 200
    recusa = client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Fechado"})
    assert recusa.status_code == 200, recusa.text
    db_session.expire_all()
    orc = db_session.query(Orcamento).filter_by(id=oid).one()
    assert orc.status == "Fechado"
    assert orc.motivo_reabertura is None
    assert _orcado_jan(client, 2096) == 70.0


def test_aprovar_reabertura_mesmo_id_acompanhamento_congelado(client, db_session):
    oid = _fechar_despesas(client, 2097, jan=100.0)
    assert client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "corrigir janeiro"},
    ).status_code == 200
    r = client.post(f"/api/v1/orcamentos/{oid}/aprovar-reabertura")
    assert r.status_code == 200, r.text
    db_session.expire_all()
    live = db_session.query(Orcamento).filter_by(id=oid).one()
    assert live.status == "Reaberto"
    snap = db_session.query(Orcamento).filter_by(ano=2097, status="Substituído").one()
    assert snap.id != oid
    assert snap.versao_base_id == oid
    assert db_session.query(OrcamentoItem).filter_by(orcamento_id=snap.id).one().jan == 100.0

    salvo = client.post("/api/v1/orcamentos/despesas/2097/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 1.0, "total_anual": 1.0}],
    })
    assert salvo.status_code == 200, salvo.text
    db_session.expire_all()
    assert db_session.query(OrcamentoItem).filter_by(orcamento_id=oid).one().jan == 1.0
    assert _orcado_jan(client, 2097) == 100.0


def test_status_nao_aprova_reabertura_sem_snapshot(client, db_session):
    oid = _fechar_despesas(client, 2098, jan=100.0)
    assert client.post(
        f"/api/v1/orcamentos/{oid}/solicitar-reabertura",
        json={"novo_status": "Solicitação Reabertura", "motivo": "não pular cópia"},
    ).status_code == 200
    bypass = client.post(f"/api/v1/orcamentos/{oid}/status", json={"novo_status": "Reaberto"})
    assert bypass.status_code == 400
    db_session.expire_all()
    live = db_session.query(Orcamento).filter_by(id=oid).one()
    assert live.status == "Solicitação Reabertura"
    assert db_session.query(Orcamento).filter_by(ano=2098, status="Substituído").count() == 0
    assert _orcado_jan(client, 2098) == 100.0
