"""Testes do parse Caixa e Bancos (BM-* receitas SP, OUT-BM-* despesas SP)."""

from app.services.sienge_bank_movement_parse import (
    build_inc_reembolso_keys,
    build_outcome_cobertura_keys,
    iter_bank_movement_despesa_lines,
    iter_bank_movement_receita_lines,
)


def test_rendimento_historico_52():
    item = {
        "bankMovementId": 9001,
        "bankMovementAmount": 1000,
        "bankMovementOperationType": "E",
        "bankMovementDate": "2026-03-15",
        "bankMovementHistoricId": 52,
        "bankMovementHistoricName": "Rendimento de aplicação",
        "financialCategories": [
            {
                "costCenterId": 70100,
                "financialCategoryId": 66,
                "financialCategoryName": "Rendimentos de Aplicações Financeiras",
                "financialCategoryRate": 100,
            }
        ],
    }
    lines = list(iter_bank_movement_receita_lines(item, "70100"))
    assert len(lines) == 1
    assert lines[0]["value"] == 1000.0
    assert lines[0]["source_id"] == "BM-9001-FC-66"


def test_duplicidade_entrada_vira_receita():
    item = {
        "bankMovementId": 746813,
        "bankMovementAmount": 1631.85,
        "bankMovementOperationType": "E",
        "bankMovementDate": "2023-01-23",
        "financialCategories": [
            {
                "costCenterId": 14201,
                "financialCategoryId": 1040105,
                "financialCategoryName": "Recebimento em Duplicidade",
                "financialCategoryRate": 56,
            }
        ],
    }
    lines = list(iter_bank_movement_receita_lines(item, "14201"))
    assert len(lines) == 1
    assert round(lines[0]["value"], 2) == 913.84
    assert lines[0]["source_id"] == "BM-746813-FC-1040105"


def test_skip_duplicidade_when_inc_exists():
    item = {
        "bankMovementId": 712688,
        "bankMovementAmount": 974.37,
        "bankMovementOperationType": "E",
        "bankMovementDate": "2022-09-21",
        "financialCategories": [
            {
                "costCenterId": 14201,
                "financialCategoryId": 1040105,
                "financialCategoryName": "Recebimento em Duplicidade",
                "financialCategoryRate": 56,
            }
        ],
    }
    skip = build_inc_reembolso_keys({(9, "Recebimento em Duplicidade"): 545.65})
    assert list(iter_bank_movement_receita_lines(item, "14201", skip_reembolso_keys=skip)) == []


def test_skip_reembolso_when_inc_exists():
    item = {
        "bankMovementId": 9002,
        "bankMovementAmount": 500,
        "bankMovementOperationType": "E",
        "bankMovementDate": "2026-06-10",
        "financialCategories": [
            {
                "costCenterId": 70100,
                "financialCategoryId": 171,
                "financialCategoryName": "Reembolso de Despesas Gerais",
                "financialCategoryRate": 100,
            }
        ],
    }
    skip = build_inc_reembolso_keys({(6, "Reembolso de Despesas Gerais"): 500.0})
    lines = list(iter_bank_movement_receita_lines(item, "70100", skip_reembolso_keys=skip))
    assert lines == []


def test_reembolso_jan_when_no_inc():
    item = {
        "bankMovementId": 9003,
        "bankMovementAmount": 13841.49,
        "bankMovementOperationType": "E",
        "bankMovementDate": "2026-01-05",
        "financialCategories": [
            {
                "costCenterId": 70100,
                "financialCategoryId": 171,
                "financialCategoryName": "Reembolso de Despesas Gerais",
                "financialCategoryRate": 100,
            }
        ],
    }
    lines = list(iter_bank_movement_receita_lines(item, "70100"))
    assert len(lines) == 1
    assert lines[0]["value"] == 13841.49


def test_ignores_saida():
    item = {
        "bankMovementId": 1,
        "bankMovementAmount": 100,
        "bankMovementOperationType": "S",
        "bankMovementDate": "2026-01-01",
        "financialCategories": [
            {
                "costCenterId": 70100,
                "financialCategoryId": 66,
                "financialCategoryName": "Rendimentos de Aplicações Financeiras",
                "financialCategoryRate": 100,
            }
        ],
    }
    assert list(iter_bank_movement_receita_lines(item, "70100")) == []


def _saida_ir(cc: int = 70100, valor: float = 24656.57) -> dict:
    return {
        "bankMovementId": 1171031,
        "bankMovementAmount": valor,
        "bankMovementOperationType": "S",
        "bankMovementDate": "2026-04-30",
        "bankMovementHistoricName": "Imposto de Renda Retido na Fonte (IRRF)",
        "financialCategories": [
            {
                "costCenterId": cc,
                "financialCategoryId": 2010401,
                "financialCategoryName": "IR sobre Aplicação",
                "financialCategoryRate": 100,
            }
        ],
    }


def test_ir_sobre_aplicacao_saida_vira_despesa():
    lines = list(iter_bank_movement_despesa_lines(_saida_ir(), "70100"))
    assert len(lines) == 1
    assert lines[0]["transaction_type"] == "OUTCOME"
    assert lines[0]["value"] == 24656.57
    assert lines[0]["source_id"] == "OUT-BM-1171031-FC-2010401"


def test_ir_sobre_aplicacao_ignora_entrada():
    item = _saida_ir()
    item["bankMovementOperationType"] = "E"
    assert list(iter_bank_movement_despesa_lines(item, "70100")) == []


def test_despesa_extrato_pula_quando_contas_a_pagar_ja_cobre():
    # CCs 14201/14202 lançam IR sobre Aplicação por título; não repetir
    skip = build_outcome_cobertura_keys({(4, "IR sobre Aplicação"): 139.93})
    lines = list(iter_bank_movement_despesa_lines(_saida_ir(14201), "14201", skip_keys=skip))
    assert lines == []


def test_despesa_extrato_ignora_outras_categorias():
    item = _saida_ir()
    item["financialCategories"][0]["financialCategoryName"] = "Serviços de Terceiros (Obra)"
    assert list(iter_bank_movement_despesa_lines(item, "70100")) == []
