"""
Trava o comportamento numérico atual (characterization).

Não descreve o domínio “ideal”: se um destes asserts falhar depois de uma
mudança, o número entregue ao usuário pode ter mudado e precisa de revalidação.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.math_engine import _apply_offset, _extract_curve
from app.api.routes.tracking import _calculate_financial_indicators
from app.services.excel_validator import _to_float, _to_int


class TestExtractCurve:
    def test_vazio(self):
        assert _extract_curve(None) == ([], 1)
        assert _extract_curve({}) == ([], 1)

    def test_nao_normaliza_quando_soma_100(self):
        meses, inicio = _extract_curve({"meses": [40.0, 60.0], "mes_inicio": 3})
        assert inicio == 3
        assert meses == [40.0, 60.0]

    def test_normaliza_quando_soma_diferente_de_100(self):
        meses, inicio = _extract_curve({"meses": [1.0, 1.0], "mes_inicio": 1})
        assert inicio == 1
        assert abs(meses[0] - 50.0) < 1e-9
        assert abs(meses[1] - 50.0) < 1e-9


class TestApplyOffset:
    def test_mes_inicio_1_sem_deslocamento(self):
        assert _apply_offset([10.0, 20.0], mes_inicio=1, prazo=4) == [10.0, 20.0, 0.0, 0.0]

    def test_mes_inicio_3(self):
        assert _apply_offset([100.0], mes_inicio=3, prazo=5) == [0.0, 0.0, 100.0, 0.0, 0.0]

    def test_estouro_de_prazo_e_ignorado(self):
        assert _apply_offset([1.0, 2.0, 3.0], mes_inicio=5, prazo=5) == [0.0, 0.0, 0.0, 0.0, 1.0]


class TestIndicadoresAcompanhamento:
    """Espelha _calculate_financial_indicators usado no acompanhamento."""

    def test_fluxo_simples_dois_meses(self):
        result = _calculate_financial_indicators(
            {"2024-01": -100.0, "2024-02": 110.0}
        )
        assert result["vida"] == 2
        assert result["tir_mensal"] is not None
        assert abs(result["tir_mensal"] - 10.0) < 1e-9
        tir_anual_esperada = ((1.1) ** 12 - 1) * 100
        assert abs(result["tir_anual"] - tir_anual_esperada) < 1e-9
        assert result["exposicao_maxima"] == -100.0
        assert result["periodo_exposicao"] == 1
        assert result["payback"] == 2

    def test_sem_troca_de_sinal_tir_fica_none(self):
        result = _calculate_financial_indicators(
            {"2024-01": 10.0, "2024-02": 10.0}
        )
        assert result["tir_anual"] is None
        assert result["tir_mensal"] is None
        assert result["exposicao_maxima"] == 0.0
        assert result["payback"] == 1

    def test_preenche_meses_faltantes_com_zero(self):
        result = _calculate_financial_indicators(
            {"2024-01": -50.0, "2024-03": 50.0}
        )
        assert result["vida"] == 3
        assert math.isclose(result["exposicao_maxima"], -50.0)


class TestExcelConverters:
    """Importação Excel: conversão atual de texto para número."""

    def test_to_float_virgula_decimal(self):
        assert _to_float("10,5") == 10.5
        assert _to_float("10.5") == 10.5
        assert _to_float("") is None
        assert _to_float(None) is None
        assert _to_float("abc") is None

    def test_to_int(self):
        assert _to_int("3") == 3
        assert _to_int(3) == 3
        assert _to_int("x") is None
