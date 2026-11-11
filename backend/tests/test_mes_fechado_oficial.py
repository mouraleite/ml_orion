"""Mês fechado oficial = tela Fechamento; forecast em mês fechado = realizado; centavos."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.actual_transaction import ActualTransaction
from app.models.fechamento import ClosedMonth
from app.services import forecast_mes_fechado as fmf
from app.services.geracao_caixa import corte_caixa


def _fechar(db, ano, meses):
    for m in meses:
        db.add(ClosedMonth(ano=ano, mes=m, fechado_por_id=1))
    db.flush()


def test_corte_pela_tabela_de_fechamento(db_session):
    assert fmf.corte_por_fechamento(db_session, 2031) is None  # sem fechamento: calendário
    _fechar(db_session, 2031, [1, 2, 3, 5])
    assert fmf.corte_por_fechamento(db_session, 2031) == 3     # 4 aberto: sequência para no 3


def test_nome_do_forecast_segue_a_tabela(db_session):
    from app.api.routes.forecasts import _descricao_forecast_rolling
    _fechar(db_session, 2032, [1, 2, 3, 4, 5, 6, 7])
    assert _descricao_forecast_rolling(2032, db_session) == "Forecast - 7+5"


def test_geracao_de_caixa_usa_a_tabela_quando_ha():
    assert corte_caixa(2026, date(2026, 11, 11), {2026: 7}) == 7
    assert corte_caixa(2026, date(2026, 11, 11), {2026: None}) == 10  # calendário de reserva


def test_mes_fechado_recebe_o_realizado_e_linha_nova_entra():
    itens = [{"produto_id": 1, "plano_financeiro_id": 10, **{m: 5.0 for m in fmf.MESES_STR}}]
    real = {(1, 10): {"jan": 100.0}, (2, 20): {"fev": 50.0}}
    out = fmf.aplicar_realizado_nos_fechados(itens, real, [1, 2])
    assert out[0]["jan"] == 100.0 and out[0]["fev"] == 0.0 and out[0]["mar"] == 5.0
    assert out[0]["total_anual"] == pytest.approx(100.0 + 5.0 * 10)
    nova = [r for r in out if r["produto_id"] == 2][0]
    assert nova["fev"] == 50.0 and nova["mar"] == 0.0 and "id" not in nova


def test_valor_gravado_e_arredondado_a_centavo(db_session):
    t = ActualTransaction(source_id="INC-CENT-1", cost_center_id=1, transaction_type="INCOME",
                          transaction_date=date(2026, 5, 1), value=281.549999999726, is_forecast=False)
    db_session.add(t)
    db_session.flush()
    db_session.expire(t)
    assert t.value == 281.55
