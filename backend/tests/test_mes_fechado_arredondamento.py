"""Mês fechado: diferença de arredondamento não bloqueia o salvamento (análise 09/11, orçamento e forecast)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.periodos import mudou


def test_arredondamento_nao_conta_como_mudanca():
    assert not mudou(1234.5600000001, 1234.56)
    assert not mudou(0.1 + 0.2, 0.3)
    assert not mudou(None, 0.0)


def test_mudanca_de_um_centavo_conta():
    assert mudou(1234.57, 1234.56)
    assert mudou(1, 0)
