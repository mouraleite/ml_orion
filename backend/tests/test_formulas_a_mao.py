"""Fórmulas conferidas com valores calculados à mão (análise 09/11: protegem contra erro, não só contra mudança).

Referências: tabela Price e SAC de 100.000 a 1% a.m. em 12 meses (HP-12C / planilha);
TIR de fluxos simples; conversão de taxa anual em mensal equivalente.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy_financial as npf
import pytest

from app.api.routes import tracking as tr
from app.services.math_engine import cronograma_funding


def test_price_100mil_1pct_12m():
    linhas = cronograma_funding(100_000.0, 0.01, 12, "Price")
    parcelas = [j + a for j, a in linhas]
    # PMT = 100.000 x 0,01 / (1 - 1,01^-12) = 8.884,88
    assert parcelas[0] == pytest.approx(8_884.88, abs=0.01)
    assert all(p == pytest.approx(8_884.88, abs=0.02) for p in parcelas)
    assert linhas[0] == (pytest.approx(1_000.00, abs=0.01), pytest.approx(7_884.88, abs=0.01))
    assert sum(j for j, _ in linhas) == pytest.approx(6_618.55, abs=0.05)  # juros totais


def test_sac_100mil_1pct_12m():
    linhas = cronograma_funding(100_000.0, 0.01, 12, "SAC")
    assert all(a == pytest.approx(8_333.33, abs=0.01) for _, a in linhas)
    assert linhas[0][0] + linhas[0][1] == pytest.approx(9_333.33, abs=0.01)   # 1ª parcela
    assert linhas[-1][0] + linhas[-1][1] == pytest.approx(8_416.67, abs=0.01)  # última
    assert sum(j for j, _ in linhas) == pytest.approx(6_500.00, abs=0.01)      # juros totais


def test_tir_de_fluxo_simples():
    assert npf.irr([-1_000.0, 1_100.0]) == pytest.approx(0.10, abs=1e-9)
    # 3 parcelas de 400 por 1.000 hoje: TIR mensal 9,7010%
    assert npf.irr([-1_000.0, 400.0, 400.0, 400.0]) == pytest.approx(0.097010, abs=1e-6)


def test_tir_do_acompanhamento_converte_mes_para_ano():
    ind = tr._calculate_financial_indicators({"2026-01": -1_000.0, "2026-02": 1_100.0})
    assert ind["tir_mensal"] == pytest.approx(10.0, abs=1e-6)
    assert ind["tir_anual"] == pytest.approx((1.10 ** 12 - 1) * 100, abs=1e-6)  # 213,84%


def test_taxa_anual_em_mensal_equivalente():
    # INCC/IPCA/juros: 12% a.a. = 0,9489% a.m. (composto), nunca 1% a.m. (simples)
    mensal = (1 + 0.12) ** (1 / 12) - 1
    assert mensal == pytest.approx(0.009489, abs=1e-6)
    assert (1 + mensal) ** 12 - 1 == pytest.approx(0.12, abs=1e-12)
