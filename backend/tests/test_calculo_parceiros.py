"""Fase 2, lote B (09/11/2026): divisão entre parceiros e cenário de velocidade de vendas.

Regra (decidida pelo Marcelo): o % de cada parceiro vale sobre o projeto inteiro;
custos rateados divididos pelo %; custos não rateados 100% dos empreendedores,
repartidos entre eles na proporção de cada um.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase import Phase
from app.models.phase_details import PhaseExchanges
from app.models.viability import Viability
from app.services.math_engine import _acelerar_curva, calculate_viability_results

CURVA_1_MES = {"meses": [100.0], "mes_inicio": 1}


def _fase(db, abertura, rateios, perc_terr=25.0):
    v = Viability(project_name="Teste parceiros")
    db.add(v)
    db.flush()
    ph = Phase(viability_id=v.id, name="Fase 1")
    db.add(ph)
    db.flush()
    db.add(ViabilityConstruction(phase_id=ph.id, custo_obras=1_000_000.0, custo_obras_tipo="R$"))
    db.add(ViabilityExpenses(
        phase_id=ph.id,
        marketing_valor=100_000.0, marketing_tipo="R$", curva_marketing_json=CURVA_1_MES,
        comercial_valor=0.0, comercial_tipo="R$", adm_valor=0.0, adm_tipo="R$",
    ))
    db.add(PhaseExchanges(
        phase_id=ph.id, modalidade="", perc_parceria_terrenista=perc_terr, perc_parceria_investidor=0.0,
        perc_parceria_empreendedor=100.0 - perc_terr, abertura_terrenistas_json=abertura, rateios_config_json=rateios,
    ))
    db.flush()
    db.expire_all()
    return calculate_viability_results(db, ph.id)


def _soma(cf, col):
    return sum(m.get(col, 0.0) or 0.0 for m in cf)


ABERTURA = [
    {"nome": "A", "tipo": "Proprietário", "percentual": 25},
    {"nome": "B", "tipo": "Empreendedor", "percentual": 45},
    {"nome": "C", "tipo": "Empreendedor", "percentual": 30},
]
RATEIOS = {"custo_obras": True, "marketing": False}


def test_rateado_pelo_percentual_e_nao_rateado_so_empreendedores(db_session):
    r = _fase(db_session, ABERTURA, RATEIOS)
    cf = r["monthly_cashflow_parceiros"]
    obras_total = _soma(r["monthly_cashflow"], "Obras")
    mkt_total = _soma(r["monthly_cashflow"], "Despesas")
    assert mkt_total == pytest.approx(100_000.0)

    a, b, c = cf["A (Proprietário)"], cf["B (Empreendedor)"], cf["C (Empreendedor)"]
    assert _soma(a, "Obras") == pytest.approx(obras_total * 0.25)
    assert _soma(b, "Obras") == pytest.approx(obras_total * 0.45)
    assert _soma(c, "Obras") == pytest.approx(obras_total * 0.30)
    # marketing não rateado: nada para o proprietário, 45/75 e 30/75 para os empreendedores
    assert _soma(a, "Despesas") == pytest.approx(0.0)
    assert _soma(b, "Despesas") == pytest.approx(100_000.0 * 45 / 75)
    assert _soma(c, "Despesas") == pytest.approx(100_000.0 * 30 / 75)


@pytest.mark.parametrize("col", ["Receitas", "Obras", "Despesas", "Impostos", "Terreno", "Fluxo_de_Caixa"])
def test_soma_dos_parceiros_e_o_global(db_session, col):
    r = _fase(db_session, ABERTURA, RATEIOS)
    soma = sum(_soma(cf, col) for cf in r["monthly_cashflow_parceiros"].values())
    assert soma == pytest.approx(_soma(r["monthly_cashflow"], col), abs=1e-6)


def test_lucro_dos_parceiros_soma_o_global(db_session):
    r = _fase(db_session, ABERTURA, RATEIOS)
    soma = sum(v["lucro_liquido"] for v in r["indicators_parceiros"].values())
    assert soma == pytest.approx(r["indicators"]["lucro_liquido"])
    assert r["aviso_parceiros"] is None


def test_visao_empreendedor_e_a_soma_dos_empreendedores(db_session):
    r = _fase(db_session, ABERTURA, RATEIOS)
    cf_emp = r["monthly_cashflow_empreendedor"]
    pars = r["monthly_cashflow_parceiros"]
    for col in ["Obras", "Despesas", "Fluxo_de_Caixa"]:
        esperado = _soma(pars["B (Empreendedor)"], col) + _soma(pars["C (Empreendedor)"], col)
        assert _soma(cf_emp, col) == pytest.approx(esperado)


def test_dre_de_despesas_acompanha_a_visao(db_session):
    r = _fase(db_session, ABERTURA, RATEIOS)
    assert r["indicators_parceiros"]["A (Proprietário)"]["dre_despesas_marketing"] == pytest.approx(0.0)
    assert r["indicators_parceiros"]["B (Empreendedor)"]["dre_despesas_marketing"] == pytest.approx(60_000.0)


def test_aviso_quando_abertura_nao_soma_100(db_session):
    r = _fase(db_session, [{"nome": "A", "tipo": "Proprietário", "percentual": 25}], RATEIOS)
    assert "25.00%" in r["aviso_parceiros"]


def test_sem_abertura_empreendedor_fica_com_o_que_sobra(db_session):
    r = _fase(db_session, [], {"custo_obras": True}, perc_terr=40.0)
    obras = _soma(r["monthly_cashflow"], "Obras")
    assert _soma(r["monthly_cashflow_empreendedor"], "Obras") == pytest.approx(obras * 0.60)
    assert r["indicators_parceiros"] == {}


# --- velocidade de vendas ------------------------------------------------------

def test_velocidade_1_nao_muda_a_curva():
    assert _acelerar_curva([10.0, 20.0, 70.0], 1.0) == [10.0, 20.0, 70.0]


def test_velocidade_2_vende_na_metade_do_tempo():
    assert _acelerar_curva([25.0, 25.0, 25.0, 25.0], 2.0) == pytest.approx([50.0, 50.0])


def test_velocidade_meia_leva_o_dobro():
    curva = _acelerar_curva([50.0, 50.0], 0.5)
    assert curva == pytest.approx([25.0, 25.0, 25.0, 25.0])


@pytest.mark.parametrize("fator", [0.3, 0.75, 1.5, 3.0])
def test_velocidade_preserva_o_total(fator):
    curva = [5.0, 15.0, 30.0, 30.0, 15.0, 5.0]
    assert sum(_acelerar_curva(curva, fator)) == pytest.approx(100.0)
