"""Testes do parse Contas a Pagar (Pagamento + financialCategoryRate)."""

from app.services.sienge_outcome_parse import (
    category_rate_ratio,
    is_pagamento,
    is_realizado_operation,
    iter_outcome_pagamento_lines,
    payment_gross_amount,
)


def test_is_pagamento_by_id():
    assert is_pagamento({"operationTypeId": 1}) is True
    assert is_pagamento({"operationTypeId": 5, "operationTypeName": "Substituição"}) is False
    assert is_pagamento({"operationTypeId": 3}) is False


def test_is_pagamento_by_name():
    assert is_pagamento({"operationTypeName": "Pagamento"}) is True
    assert is_pagamento({"operationTypeName": "Cancelamento"}) is False


def test_ops_realizado_1_e_8():
    assert is_realizado_operation({"operationTypeId": 5}) is False
    assert is_realizado_operation({"operationTypeId": 1}) is True
    assert is_realizado_operation({"operationTypeId": 8}) is True
    assert is_realizado_operation({"operationTypeId": 10}) is False


def test_payment_gross_prefers_gross_amount():
    assert payment_gross_amount({"grossAmount": 3500, "netAmount": 3340.75}) == 3500.0
    assert payment_gross_amount({"netAmount": 100}) == 100.0


def test_category_rate_prefers_financial_category_rate():
    assert category_rate_ratio({"financialCategoryRate": 87.5, "percentage": 50}) == 0.875
    assert category_rate_ratio({"percentage": 25}) == 0.25
    assert category_rate_ratio({}) == 1.0


def test_iter_exclui_substituicao_mantem_pagamento():
    item = {
        "billId": 100,
        "creditorName": "Fornecedor",
        "documentIdentificationName": "NF",
        "documentNumber": "1",
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": 55,
                "financialCategoryName": "Serviços de Terceiros (Obra)",
                "financialCategoryRate": 40,
            },
            {
                "costCenterId": 99999,
                "financialCategoryId": 99,
                "financialCategoryName": "Outro",
                "financialCategoryRate": 60,
            },
        ],
        "payments": [
            {
                "operationTypeId": 5,
                "operationTypeName": "Substituição",
                "grossAmount": 1000,
                "netAmount": 1000,
                "paymentDate": "2026-08-10",
                "sequencialNumber": 1,
            },
            {
                "operationTypeId": 1,
                "operationTypeName": "Pagamento",
                "grossAmount": 1000,
                "netAmount": 900,
                "paymentDate": "2026-08-11",
                "sequencialNumber": 2,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    assert len(lines) == 1
    assert lines[0]["value"] == 400.0  # gross 1000 × 40%
    assert lines[0]["op_id"] == 1
    assert lines[0]["source_id"] == "OUT-100-OP1-PMT-2-DT-20260811-FC-55"


def test_iter_mantem_pagamento_e_abatimento_exclui_adiantamento():
    item = {
        "billId": 300,
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": 10,
                "financialCategoryName": "Repasses",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 500,
                "paymentDate": "2026-03-01",
                "sequencialNumber": 1,
            },
            {
                "operationTypeId": 8,
                "operationTypeName": "Abatimento de adiantamento",
                "grossAmount": 200,
                "paymentDate": "2026-03-02",
                "sequencialNumber": 2,
            },
            {
                "operationTypeId": 10,
                "operationTypeName": "Adiantamento",
                "grossAmount": 70,
                "paymentDate": "2026-03-03",
                "sequencialNumber": 3,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    assert len(lines) == 2
    by_op = {l["op_id"]: l["value"] for l in lines}
    assert by_op[1] == 500.0
    assert by_op[8] == 200.0
    assert 10 not in by_op


def _item_adiantamento(rate: float, categoria: str = "Adiantamento a Parceiros") -> dict:
    return {
        "billId": 103532,
        "paymentsCategories": [
            {
                "costCenterId": 70108,
                "financialCategoryId": 77,
                "financialCategoryName": categoria,
                "financialCategoryRate": rate,
            },
        ],
        "payments": [
            {
                "operationTypeId": 10,
                "operationTypeName": "Adiantamento",
                "grossAmount": 200000,
                "paymentDate": "2026-04-29",
                "sequencialNumber": 1,
            },
        ],
    }


def test_adiantamento_parceiros_sem_rateio_entra():
    lines = list(iter_outcome_pagamento_lines(_item_adiantamento(100), "70108"))
    assert len(lines) == 1
    assert lines[0]["op_id"] == 10
    assert lines[0]["value"] == 200000.0
    assert lines[0]["source_id"] == "OUT-103532-OP10-PMT-1-DT-20260429-FC-77"


def test_adiantamento_parceiros_rateado_fica_fora():
    # título rateado entre CCs: no SP é variação de saldo, não desembolso
    assert list(iter_outcome_pagamento_lines(_item_adiantamento(56), "70108")) == []


def test_adiantamento_fornecedores_fica_fora():
    item = _item_adiantamento(100, categoria="Adiantamentos a Fornecedores")
    assert list(iter_outcome_pagamento_lines(item, "70108")) == []


def test_iter_expands_multiple_categories_same_cc():
    item = {
        "billId": 200,
        "paymentsCategories": [
            {
                "costCenterId": "70100",
                "financialCategoryId": 1,
                "financialCategoryName": "IRPJ",
                "financialCategoryRate": 60,
            },
            {
                "costCenterId": "70100",
                "financialCategoryId": 2,
                "financialCategoryName": "CSLL",
                "financialCategoryRate": 40,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 1000,
                "netAmount": 1000,
                "paymentDate": "2026-07-15",
                "sequencialNumber": 1,
            }
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "70100"))
    assert len(lines) == 2
    by_cat = {l["category_name"]: l["value"] for l in lines}
    assert by_cat["IRPJ"] == 600.0
    assert by_cat["CSLL"] == 400.0


def test_same_bill_different_months_distinct_source_ids():
    item = {
        "billId": 103772,
        "paymentsCategories": [
            {
                "costCenterId": 16001,
                "financialCategoryId": 1,
                "financialCategoryName": "Aquisição de Terrenos",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 100,
                "paymentDate": "2026-05-10",
                "sequencialNumber": 1,
            },
            {
                "operationTypeId": 1,
                "grossAmount": 200,
                "paymentDate": "2026-06-10",
                "sequencialNumber": 1,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "16001"))
    assert len(lines) == 2
    ids = sorted(l["source_id"] for l in lines)
    assert ids[0] == "OUT-103772-OP1-PMT-1-DT-20260510-FC-1"
    assert ids[1] == "OUT-103772-OP1-PMT-1-DT-20260610-FC-1"


def test_varios_pagamentos_no_mesmo_dia_nao_colidem():
    # Sienge devolve sequencialNumber=1 em todos; o id do movimento desempata
    item = {
        "billId": 101778,
        "paymentsCategories": [
            {
                "costCenterId": 14304,
                "financialCategoryId": 2030701,
                "financialCategoryName": "IPTU/ ITR e Outros Impostos",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": valor,
                "paymentDate": "2026-03-12",
                "sequencialNumber": 1,
                "bankMovements": [{"id": bm_id, "amount": valor, "historicName": "Pagamento"}],
            }
            for bm_id, valor in [(1155593, 2759.63), (1155594, 3006.45), (1155596, 1654.91)]
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "14304"))
    assert len(lines) == 3
    assert len({l["source_id"] for l in lines}) == 3
    assert sum(l["value"] for l in lines) == 7420.99
    assert lines[0]["source_id"] == (
        "OUT-101778-OP1-PMT-1-DT-20260312-BM-1155593-FC-2030701"
    )


def test_pagamento_sem_movimento_mantem_source_id_anterior():
    item = {
        "billId": 100,
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": 55,
                "financialCategoryName": "Obras",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 500,
                "paymentDate": "2026-08-11",
                "sequencialNumber": 2,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    assert lines[0]["source_id"] == "OUT-100-OP1-PMT-2-DT-20260811-FC-55"


def test_iter_retencao_from_bank_movement_usa_gross_no_pagamento():
    item = {
        "billId": 106640,
        "creditorName": "Fornecedor",
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": "202020101",
                "financialCategoryName": "Serviços de Terceiros (Obra)",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 3500.0,
                "netAmount": 3340.75,
                "taxAmount": 159.25,
                "paymentDate": "2026-08-12",
                "sequencialNumber": 1,
                "bankMovements": [
                    {
                        "id": 1208968,
                        "amount": 159.25,
                        "historicName": "Retenção impostos",
                        "bankMovementDate": "2026-08-12",
                        "paymentCategories": [
                            {
                                "costCenterId": 13900,
                                "financialCategoryId": "2090103",
                                "financialCategoryName": "(-) Retenção de ISS - Terceiros",
                                "financialCategoryRate": 100,
                            },
                        ],
                    },
                ],
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    rets = [l for l in lines if "-RET-" in l["source_id"]]
    pays = [l for l in lines if "-PMT-" in l["source_id"]]
    assert len(rets) == 1
    assert rets[0]["value"] == 159.25
    assert rets[0]["category_name"] == "(-) Retenção de ISS - Terceiros"
    assert len(pays) == 1
    assert pays[0]["value"] == 3500.0


def test_authorization_name_do_titulo():
    from app.services.sienge_outcome_parse import authorization_name

    assert authorization_name({
        "authorizations": [{"name": "Tesouraria"}],
    }) == "Tesouraria"
    assert authorization_name({
        "authorizations": [{"departmentName": "Marketing"}],
    }) == "Marketing"
    assert authorization_name({"authorizations": []}) is None
    assert authorization_name({}) is None
    assert authorization_name({
        "authorizations": [{"name": "Gestão de Contratos"}, {"name": "Tesouraria"}],
    }) == "Gestão de Contratos"


def test_authorization_name_vem_de_departaments_costs():
    """Bulk Sienge: authorizations = aprovador; departamento está em departamentsCosts."""
    from app.services.sienge_outcome_parse import authorization_name

    assert authorization_name({
        "authorizations": [{
            "authorizationUserId": "NAIARA.CASSIO",
            "authorizationUserName": "Naiara",
            "isLastToAuthorize": "N",
        }],
        "departamentsCosts": [{"id": 31, "name": "Tesouraria", "rate": 100.0}],
    }) == "Tesouraria"
    assert authorization_name({
        "departamentsCosts": [
            {"id": 23, "name": "Marketing", "rate": 40.0},
            {"id": 31, "name": "Tesouraria", "rate": 60.0},
        ],
    }) == "Tesouraria"
    assert authorization_name({
        "authorizations": [{"authorizationUserId": "X"}],
        "departamentsCosts": [],
    }) is None


def test_iter_grava_authorization_name_sem_mudar_valor():
    item = {
        "billId": 100,
        "creditorName": "Fornecedor",
        "documentIdentificationName": "NF",
        "documentNumber": "1",
        "departamentsCosts": [{"id": 12, "name": "Engenharia Obras", "rate": 100.0}],
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": 55,
                "financialCategoryName": "Serviços de Terceiros (Obra)",
                "financialCategoryRate": 40,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "operationTypeName": "Pagamento",
                "grossAmount": 1000,
                "netAmount": 900,
                "paymentDate": "2026-08-11",
                "sequencialNumber": 2,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    assert len(lines) == 1
    assert lines[0]["value"] == 400.0
    assert lines[0]["authorization_name"] == "Engenharia Obras"


def test_iter_sem_autorizacao_fica_nulo():
    item = {
        "billId": 101,
        "paymentsCategories": [
            {
                "costCenterId": 13900,
                "financialCategoryId": 55,
                "financialCategoryName": "Serviços de Terceiros (Obra)",
                "financialCategoryRate": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "grossAmount": 50,
                "paymentDate": "2026-01-02",
                "sequencialNumber": 1,
            },
        ],
    }
    lines = list(iter_outcome_pagamento_lines(item, "13900"))
    assert lines[0]["authorization_name"] is None


def test_url_contas_pagar_pede_autorizacoes():
    from app.services.sienge_sync import outcome_contas_pagar_url

    url = outcome_contas_pagar_url("13900", "2026-01-01", "2026-12-31")
    assert "withAuthorizations=true" in url
    assert "withBankMovements=true" in url
    assert "selectionType=P" in url


def _titulo_rateado_dois_produtos():
    """Título 1.500 rateado 40/60; percentage=100 em cada CC (armadilha da API)."""
    return {
        "billId": 33401,
        "creditorName": "Fornecedor",
        "documentIdentificationName": "NF",
        "documentNumber": "1",
        "paymentsCategories": [
            {
                "costCenterId": 14301,
                "financialCategoryId": 1,
                "financialCategoryName": "Obras",
                "financialCategoryRate": 40,
                "percentage": 100,
            },
            {
                "costCenterId": 14302,
                "financialCategoryId": 1,
                "financialCategoryName": "Obras",
                "financialCategoryRate": 60,
                "percentage": 100,
            },
        ],
        "payments": [
            {
                "operationTypeId": 1,
                "operationTypeName": "Pagamento",
                "netAmount": 1500,
                "grossAmount": 1500,
                "paymentDate": "2020-05-10",
                "sequencialNumber": 1,
            },
        ],
    }


def test_legacy_pmt_source_id_nao_pega_op1():
    from app.services.sienge_outcome_parse import is_legacy_pmt_source_id

    assert is_legacy_pmt_source_id("OUT-33401-PMT-1") is True
    assert is_legacy_pmt_source_id("OUT-33401-OP1-PMT-1-DT-20260510-FC-1") is False
    assert is_legacy_pmt_source_id("OUT-1-OP8-PMT-1-DT-20260101-FC-1") is False
    assert is_legacy_pmt_source_id("INC-1-BM-1-FC-1") is False


def test_rateio_pmt_historico_usa_financial_category_rate_e_nao_percentage():
    from app.services.sienge_outcome_parse import rateio_pmt_historico_do_cc

    cats = _titulo_rateado_dois_produtos()["paymentsCategories"]
    assert rateio_pmt_historico_do_cc(cats, "14301") == 0.4
    assert rateio_pmt_historico_do_cc(cats, "14302") == 0.6
    assert rateio_pmt_historico_do_cc(cats, "14399") is None


def test_iter_pmt_historico_fatia_o_titulo_e_nao_grava_op1():
    from app.services.sienge_outcome_parse import iter_pmt_historico_lines

    item = _titulo_rateado_dois_produtos()
    morada = list(iter_pmt_historico_lines(item, "14301"))
    reserva = list(iter_pmt_historico_lines(item, "14302"))
    outro = list(iter_pmt_historico_lines(item, "14399"))

    assert outro == []
    assert len(morada) == 1 and len(reserva) == 1
    assert morada[0]["source_id"] == "OUT-33401-PMT-1"
    assert reserva[0]["source_id"] == "OUT-33401-PMT-1"
    assert "-OP" not in morada[0]["source_id"]
    assert morada[0]["value"] == 600.0
    assert reserva[0]["value"] == 900.0


def test_apply_pmt_historico_corrige_copia_do_titulo_cheio_e_nao_mexe_em_op1():
    from datetime import date

    from app.models.actual_transaction import ActualTransaction
    from app.services.sienge_outcome_parse import iter_pmt_historico_lines
    from app.services.sienge_sync import apply_pmt_historico_rateio_lines

    db, _, _, _ = _sqlite_pmt_db()
    item = _titulo_rateado_dois_produtos()
    db.add_all([
        ActualTransaction(
            cost_center_id=1, source_id="OUT-33401-PMT-1",
            transaction_type="OUTCOME", category="Obras",
            transaction_date=date(2020, 5, 10), value=1500.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=2, source_id="OUT-33401-PMT-1",
            transaction_type="OUTCOME", category="Obras",
            transaction_date=date(2020, 5, 10), value=1500.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=1, source_id="OUT-33401-OP1-PMT-1-DT-20260510-FC-1",
            transaction_type="OUTCOME", category="Obras",
            transaction_date=date(2026, 5, 10), value=400.0, is_forecast=False,
        ),
    ])
    db.commit()

    class _CC:
        def __init__(self, pk, sienge):
            self.id = pk
            self.id_sienge = sienge

    apply_pmt_historico_rateio_lines(
        db, _CC(1, "14301"),
        list(iter_pmt_historico_lines(item, "14301")),
        date(2020, 1, 1), date(2020, 12, 31),
    )
    apply_pmt_historico_rateio_lines(
        db, _CC(2, "14302"),
        list(iter_pmt_historico_lines(item, "14302")),
        date(2020, 1, 1), date(2020, 12, 31),
    )

    v1 = db.query(ActualTransaction).filter_by(cost_center_id=1, source_id="OUT-33401-PMT-1").one().value
    v2 = db.query(ActualTransaction).filter_by(cost_center_id=2, source_id="OUT-33401-PMT-1").one().value
    op1 = db.query(ActualTransaction).filter_by(
        source_id="OUT-33401-OP1-PMT-1-DT-20260510-FC-1",
    ).one().value
    assert v1 == 600.0
    assert v2 == 900.0
    assert op1 == 400.0


def _sqlite_pmt_db():
    import importlib
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.database import Base

    for name in os.listdir("app/models"):
        if name.endswith(".py"):
            importlib.import_module("app.models." + name[:-3])

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), None, None, None
