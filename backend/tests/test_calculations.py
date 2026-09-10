"""
Tests for calculations.py — Seção 22 formulas + helpers do Dashboard Executivo.
Critério de aceite: valores do Dashboard devem coincidir com os do Acompanhamento.
"""
import pytest
import sys
import os

# Permite importar app sem instalar o pacote
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.calculations import (
    calculo_variacao_rs,
    calculo_variacao_perc,
    calculo_saldo_despesas,
    calcular_ranking_desvios,
    sumarizar_serie_mensal,
)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# ─── calculo_variacao_rs ────────────────────────────────────────────────────

class TestCalculoVariacaoRs:
    def test_positivo(self):
        assert calculo_variacao_rs(150.0, 100.0) == 50.0

    def test_negativo(self):
        assert calculo_variacao_rs(80.0, 100.0) == -20.0

    def test_zero(self):
        assert calculo_variacao_rs(0.0, 0.0) == 0.0

    def test_decimal(self):
        assert abs(calculo_variacao_rs(33.33, 10.0) - 23.33) < 0.001


# ─── calculo_variacao_perc ──────────────────────────────────────────────────

class TestCalculoVariacaoPerc:
    def test_positivo(self):
        result = calculo_variacao_perc(120.0, 100.0)
        assert abs(result - 0.20) < 1e-9

    def test_negativo(self):
        result = calculo_variacao_perc(80.0, 100.0)
        assert abs(result - (-0.20)) < 1e-9

    def test_divisao_por_zero_positivo(self):
        # Se referência é 0 mas há realizado positivo → 100%
        assert calculo_variacao_perc(50.0, 0.0) == 1.0

    def test_divisao_por_zero_zero(self):
        # 0 / 0 → 0%
        assert calculo_variacao_perc(0.0, 0.0) == 0.0

    def test_divisao_por_zero_negativo(self):
        # negativo / 0 → -100%
        assert calculo_variacao_perc(-10.0, 0.0) == -1.0

    def test_identico(self):
        assert calculo_variacao_perc(100.0, 100.0) == 0.0


# ─── calculo_saldo_despesas ─────────────────────────────────────────────────

class TestCalculoSaldoDespesas:
    def test_saldo_positivo(self):
        # Gastou menos que o previsto → saldo positivo (sobrou orçamento)
        assert calculo_saldo_despesas(1000.0, 800.0) == 200.0

    def test_saldo_negativo(self):
        # Gastou mais → estouro
        assert calculo_saldo_despesas(800.0, 1000.0) == -200.0

    def test_saldo_zero(self):
        assert calculo_saldo_despesas(500.0, 500.0) == 0.0


# ─── calcular_ranking_desvios ───────────────────────────────────────────────

def _make_item(prod_id, plano_id, ref, real):
    return {
        "produto_id": prod_id,
        "plano_financeiro_id": plano_id,
        "orcado": {"total": ref},
        "realizado": {"total": real},
    }


class TestCalcularRankingDesvios:
    def test_ordem_decrescente_por_abs(self):
        itens = [
            _make_item(1, 1, 100, 110),   # desvio +10
            _make_item(2, 2, 100, 50),    # desvio -50  ← maior em abs
            _make_item(3, 3, 100, 130),   # desvio +30
        ]
        ranking = calcular_ranking_desvios(itens, modo="orcado", top_n=3)
        # Deve ser ordenado por variacao_abs desc
        assert ranking[0]["produto_id"] == 2
        assert ranking[1]["produto_id"] == 3
        assert ranking[2]["produto_id"] == 1

    def test_top_n_limita(self):
        itens = [_make_item(i, i, 100, 100 + i * 10) for i in range(20)]
        ranking = calcular_ranking_desvios(itens, top_n=5)
        assert len(ranking) == 5

    def test_vazio(self):
        assert calcular_ranking_desvios([], top_n=10) == []

    def test_variacao_correta(self):
        itens = [_make_item(1, 1, 200.0, 100.0)]
        r = calcular_ranking_desvios(itens, modo="orcado")[0]
        assert r["variacao_rs"] == -100.0
        assert abs(r["variacao_perc"] - (-0.5)) < 1e-9
        assert r["variacao_abs"] == 100.0


# ─── sumarizar_serie_mensal ─────────────────────────────────────────────────

def _make_serie_item(prod_id, orcado_jan=0.0, realizado_jan=0.0, total_orc=0.0, total_real=0.0):
    meses = {m: 0.0 for m in MESES}
    meses["jan"] = orcado_jan
    orcado = {**meses, "total": total_orc}

    meses_real = {m: 0.0 for m in MESES}
    meses_real["jan"] = realizado_jan
    realizado = {**meses_real, "total": total_real}

    return {
        "produto_id": prod_id,
        "orcado": orcado,
        "forecast": {m: 0.0 for m in MESES + ["total"]},
        "realizado": realizado,
    }


class TestSumarizarSerieMensal:
    def test_soma_dois_itens(self):
        itens = [
            _make_serie_item(1, orcado_jan=100.0, realizado_jan=80.0, total_orc=1200.0, total_real=960.0),
            _make_serie_item(2, orcado_jan=200.0, realizado_jan=220.0, total_orc=2400.0, total_real=2640.0),
        ]
        serie = sumarizar_serie_mensal(itens, "orcado")
        assert serie["orcado"]["jan"] == 300.0
        assert serie["realizado"]["jan"] == 300.0
        assert serie["orcado"]["total"] == 3600.0
        assert serie["realizado"]["total"] == 3600.0

    def test_vazio(self):
        serie = sumarizar_serie_mensal([], "orcado")
        assert serie["orcado"]["total"] == 0.0
        assert serie["realizado"]["total"] == 0.0

    def test_estrutura_retorno(self):
        serie = sumarizar_serie_mensal([], "orcado")
        assert "orcado" in serie
        assert "forecast" in serie
        assert "realizado" in serie
        for tp in ["orcado", "forecast", "realizado"]:
            assert "total" in serie[tp]
            for m in MESES:
                assert m in serie[tp]


# ─── Teste de Consistência: Dashboard == Acompanhamento ─────────────────────
class TestConsistenciaValores:
    """
    Garante que os valores calculados pelo Dashboard (via sumarizar_serie_mensal)
    são matematicamente idênticos aos que o Acompanhamento retornaria
    para os mesmos dados de entrada.
    Critério de aceite CA-001.
    """
    def test_dashboard_bate_com_acompanhamento(self):
        itens_acompanhamento = [
            _make_serie_item(1, orcado_jan=500.0, realizado_jan=450.0, total_orc=6000.0, total_real=5400.0),
            _make_serie_item(2, orcado_jan=300.0, realizado_jan=320.0, total_orc=3600.0, total_real=3840.0),
        ]

        # O que o Acompanhamento reportaria como total realizado
        total_acomp_real = sum(
            item["realizado"]["total"] for item in itens_acompanhamento
        )  # 5400 + 3840 = 9240

        # O que o Dashboard computaria via sumarizar_serie_mensal
        serie = sumarizar_serie_mensal(itens_acompanhamento, "orcado")

        assert serie["realizado"]["total"] == total_acomp_real, (
            f"Dashboard ({serie['realizado']['total']}) ≠ Acompanhamento ({total_acomp_real})"
        )


class TestAgregarSerieVendasLiquido:
    def test_vendas_menos_distratos(self):
        from app.services.calculations import agregar_serie_vendas_liquido

        itens = [
            {
                "vendas": {
                    "realizado": {
                        "jan": {"vgv": 1000.0, "unidades": 2},
                        "fev": {"vgv": 500.0, "unidades": 1},
                    }
                },
                "distratos": {
                    "realizado": {
                        "jan": {"vgv": 200.0, "unidades": 1},
                    }
                },
            },
            {
                "vendas": {
                    "realizado": {
                        "jan": {"vgv": 300.0, "unidades": 1},
                    }
                },
                "distratos": {"realizado": {}},
            },
        ]
        serie = agregar_serie_vendas_liquido(itens)
        assert serie["realizado"]["jan"]["vgv"] == 1100.0
        assert serie["realizado"]["jan"]["unidades"] == 2
        assert serie["realizado"]["fev"]["vgv"] == 500.0
