"""TIR que não converge vira None ("n/d" na tela), nunca 0% (análise 09/11)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.routes import tracking as tr


def test_fluxo_sem_troca_de_sinal_nao_tem_tir():
    ind = tr._calculate_financial_indicators({"2026-01": 100.0, "2026-02": 50.0})
    assert ind["tir_anual"] is None and ind["tir_mensal"] is None


def test_fluxo_normal_tem_tir():
    ind = tr._calculate_financial_indicators({"2026-01": -100.0, "2026-02": 0.0, "2026-03": 120.0})
    assert ind["tir_anual"] is not None and ind["tir_anual"] > 0
