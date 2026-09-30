"""Testes do realizado de despesas via Sienge OUT-*."""

from datetime import date

import pytest

from app.models.actual_transaction import ActualTransaction
from app.models.financial_plan import FinancialPlan


def _criar_orcamento_despesas(client, ano):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano,
        "tipo": "DESPESAS",
        "produto_id": 1,
    })
    assert r.status_code == 200, r.text
    return r.json()["orcamento_id"]


class TestRealizadoSiengeDespesas:
    def test_acompanhamento_agrega_parcela_out(self, client, db_session):
        ano = 2048
        plan = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
        assert plan is not None

        _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "mar": 1000.0,
                "total_anual": 1000.0,
            }]
        })

        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="OUT-999-OP1-PMT-1-DT-20480315-FC-1",
                transaction_type="OUTCOME",
                category=plan.name,
                transaction_date=date(ano, 3, 15),
                value=750.0,
                is_forecast=False,
                authorization_name="Marketing",
                bill_id="999",
            )
        )
        db_session.commit()

        resp = client.get(f"/api/v1/acompanhamento/despesas/{ano}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("realizado_fonte") == "sienge_contas_pagar"

        item = next(
            i for i in data["itens"]
            if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
        )
        assert item["realizado"]["mar"] == 750.0
        assert item["realizado"]["total"] == 750.0
        assert item["saldo_orcado"]["mar"] == 250.0

    def test_drill_total_bate_matriz(self, client, db_session):
        ano = 2049
        plan = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
        assert plan is not None

        _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 500.0,
                "fev": 500.0,
                "total_anual": 1000.0,
            }]
        })

        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="OUT-1000-OP1-PMT-1-DT-20490110-FC-1",
                transaction_type="OUTCOME",
                category=plan.name,
                transaction_date=date(ano, 1, 10),
                value=400.0,
                is_forecast=False,
                authorization_name="Marketing",
            )
        )
        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="OUT-1000-OP1-PMT-2-DT-20490210-FC-1",
                transaction_type="OUTCOME",
                category=plan.name,
                transaction_date=date(ano, 2, 10),
                value=100.0,
                is_forecast=False,
                authorization_name="Marketing",
            )
        )
        db_session.commit()

        acomp = client.get(f"/api/v1/acompanhamento/despesas/{ano}").json()
        item = next(
            i for i in acomp["itens"]
            if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
        )
        matriz_total = item["realizado"]["total"]

        drill = client.get(
            f"/api/v1/dashboard/realizado-despesas/{ano}?produto_id=1&plano_id=1",
        ).json()
        drill_total = sum(t["valor"] for t in drill["transacoes"])

        assert matriz_total == drill_total == 500.0


def test_source_id_realizado_despesa_segue_premissas_cp():
    from app.services.realizado_sienge import source_id_realizado_despesa

    assert source_id_realizado_despesa("OUT-108564-OP1-PMT-1-DT-20260901-FC-1") is True
    assert source_id_realizado_despesa("OUT-1-OP8-PMT-1-DT-20260101-FC-1") is True
    assert source_id_realizado_despesa("OUT-103532-OP10-PMT-1-DT-20260429-FC-77") is True
    assert source_id_realizado_despesa("OUT-999-RET-BM-1-FC-1") is True
    assert source_id_realizado_despesa("OUT-TARIFA-INC-1") is True
    assert source_id_realizado_despesa("OUT-AFAC-INC-1") is True
    assert source_id_realizado_despesa("OUT-BM-1171031-FC-2010401") is True
    # formato antigo: Substituição/Cancelamento gravados sem filtrar operação
    assert source_id_realizado_despesa("OUT-108564-PMT-1") is False
    assert source_id_realizado_despesa("OUT-90870-PMT-1") is False
    assert source_id_realizado_despesa("FCST-OUT-108976-1") is False
    assert source_id_realizado_despesa("SIENGE-OUT-1-0") is False


def test_query_parcelas_ignora_formato_antigo_nao_pagamento(db_session):
    from app.services.realizado_sienge import query_parcelas_contas_pagar

    ano = 2053
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="OUT-108564-PMT-1",
            transaction_type="OUTCOME",
            category="Serviços de Terceiros (Obra)",
            transaction_date=date(ano, 9, 1),
            value=10400.0,
            is_forecast=False,
        )
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="OUT-108564-OP1-PMT-1-DT-20260901-FC-1",
            transaction_type="OUTCOME",
            category="Serviços de Terceiros (Obra)",
            transaction_date=date(ano, 9, 1),
            value=200.0,
            is_forecast=False,
        )
    )
    db_session.commit()

    rows = query_parcelas_contas_pagar(db_session, ano, [1])
    assert [r.source_id for r in rows] == ["OUT-108564-OP1-PMT-1-DT-20260901-FC-1"]
    assert rows[0].value == 200.0


def _matriz_vazia():
    matriz = {}

    def init_key(cc, pl):
        matriz.setdefault((cc, pl), {"realizado": {m: 0.0 for m in MESES}})

    return matriz, init_key


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@pytest.mark.parametrize("agrupado", [False, True])
def test_agregado_despesas_bate_linha_a_linha_com_retencao(db_session, agrupado):
    from app.services.realizado_sienge import (
        agregar_realizado_despesas_sienge,
        build_planos_maps,
        query_parcelas_contas_pagar,
        valor_despesa_sienge,
    )

    ano = 2056 if agrupado else 2054
    comum = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
    retencao = FinancialPlan(
        db_id=f"999010{int(agrupado)}", name=f"Retenção de Teste {ano}", tp_conta="R", fl_redutora="N"
    )
    db_session.add(retencao)
    db_session.commit()

    linhas = [
        (comum.name, date(ano, 1, 5), 100.0),
        (comum.name, date(ano, 1, 20), -30.0),
        (comum.name, date(ano, 2, 3), 55.55),
        (retencao.name, date(ano, 1, 7), 10.0),
        (retencao.name, date(ano, 1, 8), -4.0),
        (retencao.name, date(ano, 3, 9), 2.5),
    ]
    for i, (cat, dt, val) in enumerate(linhas):
        db_session.add(ActualTransaction(
            cost_center_id=1,
            source_id=f"OUT-{7000 + i}-OP1-PMT-1-DT-{dt:%Y%m%d}-FC-1",
            transaction_type="OUTCOME",
            category=cat,
            transaction_date=dt,
            value=val,
            is_forecast=False,
        ))
    db_session.commit()

    planos = [comum.id, retencao.id]
    matriz, init_key = _matriz_vazia()
    agregar_realizado_despesas_sienge(matriz, init_key, db_session, ano, [1], planos, agrupado=agrupado)

    esperado, init_esp = _matriz_vazia()
    ids, redutora = build_planos_maps(db_session)
    for r in query_parcelas_contas_pagar(db_session, ano, [1]):
        pl = ids[r.category]
        init_esp(r.cost_center_id, pl)
        esperado[(r.cost_center_id, pl)]["realizado"][MESES[r.transaction_date.month - 1]] += (
            valor_despesa_sienge(r.value, pl, r.category, redutora)
        )

    assert matriz.keys() == esperado.keys()
    for k in esperado:
        for m in MESES:
            assert round(matriz[k]["realizado"][m], 2) == round(esperado[k]["realizado"][m], 2)
    assert round(matriz[(1, retencao.id)]["realizado"]["jan"], 2) == -14.0
    assert round(matriz[(1, comum.id)]["realizado"]["jan"], 2) == 70.0


@pytest.mark.parametrize("agrupado", [False, True])
def test_agregado_receitas_exclui_afac_e_soma_por_mes(db_session, agrupado):
    from app.services.realizado_sienge import agregar_realizado_receitas_sienge

    ano = 2057 if agrupado else 2055
    plan = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
    for i, (cat, dt, val) in enumerate([
        (plan.name, date(ano, 5, 1), 40.0),
        (plan.name, date(ano, 5, 30), 60.0),
        ("AFAC", date(ano, 5, 2), 999.0),
    ]):
        db_session.add(ActualTransaction(
            cost_center_id=1,
            source_id=f"INC-{8000 + i}-{ano}-BM-1-FC-1",
            transaction_type="INCOME",
            category=cat,
            transaction_date=dt,
            value=val,
            is_forecast=False,
        ))
    db_session.commit()

    matriz, init_key = _matriz_vazia()
    agregar_realizado_receitas_sienge(matriz, init_key, db_session, ano, [1], [plan.id], agrupado=agrupado)
    assert list(matriz.keys()) == [(1, plan.id)]
    assert matriz[(1, plan.id)]["realizado"]["mai"] == 100.0


def _criar_orcamento_receitas(client, ano):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano,
        "tipo": "RECEITAS",
        "produto_id": 1,
    })
    assert r.status_code == 200, r.text
    return r.json()["orcamento_id"]


class TestRealizadoSiengeReceitas:
    def test_acompanhamento_agrega_inc_e_ignora_sp_mig(self, client, db_session):
        ano = 2050
        plan = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
        assert plan is not None

        _criar_orcamento_receitas(client, ano)
        client.post(f"/api/v1/orcamentos/receitas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "mar": 1000.0,
                "total_anual": 1000.0,
            }]
        })

        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="INC-999-BM-1-FC-1",
                transaction_type="INCOME",
                category=plan.name,
                transaction_date=date(ano, 3, 15),
                value=800.0,
                is_forecast=False,
            )
        )
        # SharePoint legado não deve entrar no realizado
        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="SP-MIG-CC1-FP1-205003",
                transaction_type="INCOME",
                category=plan.name,
                transaction_date=date(ano, 3, 1),
                value=9999.0,
                is_forecast=False,
            )
        )
        db_session.commit()

        resp = client.get(f"/api/v1/acompanhamento/receitas/{ano}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("realizado_fonte") == "sienge_contas_receber_e_caixa_bancos"

        item = next(
            i for i in data["itens"]
            if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
        )
        assert item["realizado"]["mar"] == 800.0
        assert item["realizado"]["total"] == 800.0

    def test_acompanhamento_agrega_bm_rendimentos(self, client, db_session):
        ano = 2051
        plan = db_session.query(FinancialPlan).filter(FinancialPlan.id == 1).first()
        assert plan is not None

        _criar_orcamento_receitas(client, ano)
        client.post(f"/api/v1/orcamentos/receitas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "abr": 1000.0,
                "total_anual": 1000.0,
            }]
        })

        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id="BM-42-FC-66",
                transaction_type="INCOME",
                category=plan.name,
                transaction_date=date(ano, 4, 10),
                value=250.0,
                is_forecast=False,
            )
        )
        db_session.commit()

        resp = client.get(f"/api/v1/acompanhamento/receitas/{ano}")
        assert resp.status_code == 200, resp.text
        item = next(
            i for i in resp.json()["itens"]
            if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
        )
        assert item["realizado"]["abr"] == 250.0


def test_categoria_afac_excluida_receita():
    from app.services.realizado_sienge import categoria_excluida_receita_realizado

    assert categoria_excluida_receita_realizado("AFAC") is True
    assert categoria_excluida_receita_realizado(" afac ") is True
    assert categoria_excluida_receita_realizado("Receita de Venda de Lotes") is False


def test_query_recebimentos_exclui_afac(db_session):
    from app.services.realizado_sienge import query_recebimentos_contas_receber

    ano = 2052
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="INC-AFAC-KEEP-OUT",
            transaction_type="INCOME",
            category="AFAC",
            transaction_date=date(ano, 7, 15),
            value=300000.0,
            is_forecast=False,
        )
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="INC-OK-1",
            transaction_type="INCOME",
            category="Receita de Venda de Lotes",
            transaction_date=date(ano, 7, 16),
            value=100.0,
            is_forecast=False,
        )
    )
    db_session.commit()

    rows = query_recebimentos_contas_receber(db_session, ano, [1])
    assert all((r.category or "").strip().upper() != "AFAC" for r in rows)
    assert any(r.source_id == "INC-OK-1" for r in rows)
