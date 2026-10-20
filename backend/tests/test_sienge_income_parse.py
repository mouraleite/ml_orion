"""Testes do parse Contas a Receber (Recebimento + bankMovement E/S)."""

from app.services.sienge_income_parse import (
    is_recebimento,
    iter_income_bank_lines,
    rateio_previsto_do_cc,
)


def test_is_recebimento():
    assert is_recebimento({"operationTypeId": 2}) is True
    assert is_recebimento({"operationTypeId": 7, "operationTypeName": "Distrato"}) is False
    assert is_recebimento({"operationTypeName": "Recebimento"}) is True


def test_iter_splits_receita_and_tarifa():
    item = {
        "billId": 1010,
        "clientName": "Cliente X",
        "documentIdentificationName": "Contrato",
        "documentNumber": "9",
        "receiptsCategories": [
            {"costCenterId": 13100, "financialCategoryName": "Receita de Venda de Lotes", "financialCategoryRate": 87.2},
            {"costCenterId": 13101, "financialCategoryName": "Receita de Venda de Lotes", "financialCategoryRate": 12.8},
        ],
        "receipts": [
            {
                "operationTypeId": 7,
                "operationTypeName": "Distrato",
                "netAmount": 100,
                "paymentDate": "2026-01-05",
                "bankMovements": [
                    {
                        "operationType": "E",
                        "id": 1,
                        "amount": 100,
                        "bankMovementDate": "2026-01-05",
                        "financialCategories": [
                            {"costCenterId": 13100, "financialCategoryId": 1, "financialCategoryName": "X", "financialCategoryRate": 100},
                        ],
                    }
                ],
            },
            {
                "operationTypeId": 2,
                "operationTypeName": "Recebimento",
                "netAmount": 900.34,
                "paymentDate": "2026-01-05",
                "sequencialNumber": 1,
                "bankMovements": [
                    {
                        "operationType": "E",
                        "operationName": "Recebimento",
                        "id": 10,
                        "amount": 878.14,
                        "correctedAmount": 878.14,
                        "bankMovementDate": "2026-01-05",
                        "historicName": "Recebimento",
                        "financialCategories": [
                            {
                                "costCenterId": 13100,
                                "financialCategoryId": 50,
                                "financialCategoryName": "Receita de Venda de Lotes",
                                "financialCategoryRate": 87.2,
                            },
                            {
                                "costCenterId": 13101,
                                "financialCategoryId": 50,
                                "financialCategoryName": "Receita de Venda de Lotes",
                                "financialCategoryRate": 12.8,
                            },
                        ],
                    },
                    {
                        "operationType": "E",
                        "id": 11,
                        "amount": 22.2,
                        "correctedAmount": 22.2,
                        "bankMovementDate": "2026-01-05",
                        "historicName": "Recebimento acréscimo",
                        "financialCategories": [
                            {
                                "costCenterId": 13100,
                                "financialCategoryId": 60,
                                "financialCategoryName": "Juros Ativos",
                                "financialCategoryRate": 87.2,
                            },
                        ],
                    },
                    {
                        "operationType": "S",
                        "operationName": "Pagamento",
                        "id": 12,
                        "amount": 1.33,
                        "correctedAmount": 1.33,
                        "bankMovementDate": "2026-01-05",
                        "historicName": "Pag. tarifa bancária cobrança",
                        "financialCategories": [
                            {
                                "costCenterId": 13100,
                                "financialCategoryId": 70,
                                "financialCategoryName": "Despesas Bancárias",
                                "financialCategoryRate": 87.2,
                            },
                            {
                                "costCenterId": 13101,
                                "financialCategoryId": 70,
                                "financialCategoryName": "Despesas Bancárias",
                                "financialCategoryRate": 12.8,
                            },
                        ],
                    },
                ],
            },
        ],
    }

    lines_13100 = list(iter_income_bank_lines(item, "13100"))
    # Distrato ignorado; E principal + E juros + S tarifa
    assert len(lines_13100) == 3

    income = [l for l in lines_13100 if l["transaction_type"] == "INCOME"]
    outcome = [l for l in lines_13100 if l["transaction_type"] == "OUTCOME"]
    assert len(income) == 2
    assert len(outcome) == 1

    by_cat = {l["category_name"]: round(l["value"], 4) for l in lines_13100}
    assert by_cat["Receita de Venda de Lotes"] == round(878.14 * 0.872, 4)
    assert by_cat["Juros Ativos"] == round(22.2 * 0.872, 4)
    assert by_cat["Despesas Bancárias"] == round(1.33 * 0.872, 4)
    assert outcome[0]["source_id"].startswith("OUT-TARIFA-")
    assert income[0]["source_id"].startswith("INC-")


def test_rateio_previsto_nao_grava_titulo_cheio_no_outro_cc():
    cats = [
        {"costCenterId": 13700, "financialCategoryName": "Receita de Venda de Lotes", "financialCategoryRate": 60},
        {"costCenterId": 13701, "financialCategoryName": "Receita de Venda de Lotes", "financialCategoryRate": 40},
    ]
    fatia_ml = rateio_previsto_do_cc(cats, "13700", "Receita de Venda de Lotes")
    fatia_parc = rateio_previsto_do_cc(cats, "13701", "Receita de Venda de Lotes")
    assert fatia_ml == (0.6, "Receita de Venda de Lotes")
    assert fatia_parc == (0.4, "Receita de Venda de Lotes")
    assert rateio_previsto_do_cc(cats, "13800", "Receita de Venda de Lotes") is None
    assert rateio_previsto_do_cc([], "13700", "Receita de Venda de Lotes") is None
    assert rateio_previsto_do_cc(None, "13700", "Receita de Venda de Lotes") is None
