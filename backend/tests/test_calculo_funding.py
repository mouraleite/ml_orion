"""Fase 2, lote A (09/11/2026): funding (Banco/CRI), lucro, horizonte, DRE de obras e fase inexistente."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.construction import ViabilityConstruction
from app.models.phase import Phase
from app.models.phase_details import PhaseFunding
from app.models.viability import Viability
from app.services.math_engine import (
    calculate_viability_results,
    cronograma_funding,
    taxa_mensal_funding,
)


class _F:
    def __init__(self, taxa, periodicidade=None):
        self.taxa_juros = taxa
        self.taxa_juros_periodicidade = periodicidade


# --- taxa -------------------------------------------------------------------

def test_taxa_ao_ano_vira_mensal_equivalente():
    assert taxa_mensal_funding(_F(12.0, "a.a.")) == pytest.approx(1.12 ** (1 / 12) - 1)


def test_taxa_sem_periodicidade_e_tratada_como_ao_ano():
    # registros antigos: a tela sempre pediu "% a.a."
    assert taxa_mensal_funding(_F(12.0, None)) == pytest.approx(1.12 ** (1 / 12) - 1)


def test_taxa_ao_mes_e_usada_direto():
    assert taxa_mensal_funding(_F(1.0, "a.m.")) == pytest.approx(0.01)


def test_taxa_zero():
    assert taxa_mensal_funding(_F(0.0, "a.a.")) == 0.0


# --- cronograma ---------------------------------------------------------------

@pytest.mark.parametrize("sistema", ["SAC", "Price", "Bullet"])
@pytest.mark.parametrize("taxa", [0.0, 0.01])
def test_cronograma_devolve_todo_o_principal(sistema, taxa):
    linhas = cronograma_funding(1_000_000.0, taxa, 24, sistema)
    assert len(linhas) == 24
    assert sum(a for _, a in linhas) == pytest.approx(1_000_000.0)


def test_sac_juros_sobre_saldo():
    linhas = cronograma_funding(1200.0, 0.01, 12, "SAC")
    assert linhas[0] == pytest.approx((12.0, 100.0))
    assert linhas[-1] == pytest.approx((1.0, 100.0))


def test_price_parcela_constante():
    linhas = cronograma_funding(10_000.0, 0.01, 12, "Price")
    parcelas = [j + a for j, a in linhas]
    assert max(parcelas) == pytest.approx(min(parcelas))


def test_bullet_principal_no_fim():
    linhas = cronograma_funding(1000.0, 0.02, 3, "Bullet")
    assert linhas == [pytest.approx((20.0, 0.0)), pytest.approx((20.0, 0.0)), pytest.approx((20.0, 1000.0))]


# --- motor -------------------------------------------------------------------

def _fase(db, funding=None, custo_obras=6_000_000.0):
    v = Viability(project_name="Teste funding")
    db.add(v)
    db.flush()
    ph = Phase(viability_id=v.id, name="Fase 1")
    db.add(ph)
    db.flush()
    db.add(ViabilityConstruction(phase_id=ph.id, custo_obras=custo_obras))
    if funding:
        db.add(PhaseFunding(phase_id=ph.id, **funding))
    db.flush()
    db.expire_all()
    return ph.id


def _soma(cf, col):
    return sum(m.get(col, 0.0) or 0.0 for m in cf)


BANCO = dict(tipo_funding="Plano Empresarial (Banco)", modo_volume="fixo", volume_fixo=10_000_000.0,
             taxa_juros=12.0, prazo_meses=36, sistema_amortizacao_banco="SAC")


def test_banco_juros_com_taxa_anual_convertida(db_session):
    r = calculate_viability_results(db_session, _fase(db_session, BANCO))
    cf = r["monthly_cashflow"]
    juros = _soma(cf, "Funding_Despesas") - _soma(cf, "Funding_Amortizacao")
    tx = 1.12 ** (1 / 12) - 1
    esperado = sum((10_000_000 - 10_000_000 / 36 * j) * tx for j in range(36))
    assert juros == pytest.approx(esperado, rel=1e-9)
    assert _soma(cf, "Funding_Amortizacao") == pytest.approx(10_000_000.0)


def test_banco_taxa_ao_mes(db_session):
    r = calculate_viability_results(db_session, _fase(db_session, {**BANCO, "taxa_juros": 1.0, "taxa_juros_periodicidade": "a.m."}))
    cf = r["monthly_cashflow"]
    juros = _soma(cf, "Funding_Despesas") - _soma(cf, "Funding_Amortizacao")
    assert juros == pytest.approx(sum((10_000_000 - 10_000_000 / 36 * j) * 0.01 for j in range(36)), rel=1e-9)


def test_lucro_cai_so_pelos_juros(db_session):
    base = calculate_viability_results(db_session, _fase(db_session))["indicators"]["lucro_liquido"]
    r = calculate_viability_results(db_session, _fase(db_session, BANCO))
    cf = r["monthly_cashflow"]
    juros = _soma(cf, "Funding_Despesas") - _soma(cf, "Funding_Amortizacao")
    assert base - r["indicators"]["lucro_liquido"] == pytest.approx(juros, rel=1e-9)
    assert r["indicators"]["custo_financeiro_funding"] == pytest.approx(juros, rel=1e-9)


def test_parcelas_alem_do_horizonte_estendem_o_fluxo(db_session):
    r = calculate_viability_results(db_session, _fase(db_session, {**BANCO, "taxa_juros": 0.0, "prazo_meses": 300}))
    cf = r["monthly_cashflow"]
    assert len(cf) >= 301
    assert _soma(cf, "Funding_Despesas") == pytest.approx(10_000_000.0)
    assert [m["Mes"] for m in cf] == list(range(1, len(cf) + 1))


def test_cri_devolve_principal_e_cobra_juros(db_session):
    cri = dict(tipo_funding="CRI", modo_volume="fixo", volume_fixo=3_000_000.0, taxa_juros=12.0,
               prazo_meses=12, sistema_amortizacao_banco="SAC", gross_up=0.0)
    r = calculate_viability_results(db_session, _fase(db_session, cri))
    cf = r["monthly_cashflow"]
    assert _soma(cf, "Funding_Entrada") == pytest.approx(3_000_000.0)
    assert _soma(cf, "Funding_Amortizacao") == pytest.approx(3_000_000.0)
    juros = _soma(cf, "Funding_Despesas") - _soma(cf, "Funding_Amortizacao")
    tx = 1.12 ** (1 / 12) - 1
    juros_sac = sum((3_000_000 - 3_000_000 / 12 * j) * tx for j in range(12))
    assert juros >= juros_sac  # juros + custos de estruturação


def test_tipo_nenhum_nao_gera_funding(db_session):
    r = calculate_viability_results(db_session, _fase(db_session, {**BANCO, "tipo_funding": "Nenhum"}))
    cf = r["monthly_cashflow"]
    assert _soma(cf, "Funding_Entrada") == 0.0
    assert _soma(cf, "Funding_Despesas") == 0.0


def test_linhas_da_dre_de_obras_somam_o_total(db_session):
    r = calculate_viability_results(db_session, _fase(db_session))
    ind = r["indicators"]
    linhas = (ind["dre_obras_infraestrutura"] + ind["dre_obras_projetos"] + ind["dre_obras_aquisicao"]
              + ind["dre_obras_adm"] + ind["dre_obras_extras"])
    assert linhas == pytest.approx(ind["custo_obras"])
    assert ind["dre_obras_infraestrutura"] == pytest.approx(_soma(r["monthly_cashflow"], "Obras_Custo"))


def test_fase_inexistente_retorna_erro(db_session):
    assert calculate_viability_results(db_session, 987654) == {"error": "Phase not found"}
