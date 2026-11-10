"""Fase 2: TMA do acompanhamento, rentabilidade, injeção do forecast de vendas em receitas."""
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.models.departamento import DepartamentoCostCenter
from app.models.financial_plan import FinancialPlan
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.payment_plan import PaymentPlan
from app.models.viability import Viability
from app.api.routes import tracking as tr
from app.services import injecao_receitas as inj

HOJE = datetime(2026, 11, 10)


# ---------------- TMA ----------------

def test_tma_vem_da_viabilidade_ligada_a_obra(db_session):
    cc = CostCenter(id=9101, nome="Obra X", id_sienge="91010")
    db_session.add(cc)
    db_session.flush()
    db_session.add(Viability(project_name="X", taxa_desconto_vpl=15.0, obra_cost_center_id=cc.id))
    db_session.flush()
    db_session.info.pop("_tma_por_cc", None)
    assert tr._tma_anual(db_session, [cc.id]) == pytest.approx(0.15)
    assert tr._tma_anual(db_session, [999999]) == pytest.approx(0.12)  # sem vínculo: 12%


def test_versao_de_viabilidade_nao_define_a_tma(db_session):
    cc = CostCenter(id=9102, nome="Obra Y", id_sienge="91020")
    db_session.add(cc)
    db_session.flush()
    v = Viability(project_name="Y", taxa_desconto_vpl=10.0, obra_cost_center_id=cc.id)
    db_session.add(v)
    db_session.flush()
    db_session.add(Viability(project_name="Y v2", taxa_desconto_vpl=30.0, obra_cost_center_id=cc.id, version_of_id=v.id))
    db_session.flush()
    db_session.info.pop("_tma_por_cc", None)
    assert tr._tma_anual(db_session, [cc.id]) == pytest.approx(0.10)


def test_mtir_usa_a_tma_informada():
    cf = {"2026-01": -1000.0, "2026-02": 600.0, "2026-03": 0.0, "2026-04": 700.0}
    a = tr._calculate_financial_indicators(cf)
    b = tr._calculate_financial_indicators(cf, tma_anual=0.30)
    assert a["mtir_anual"] != pytest.approx(b["mtir_anual"])
    assert tr._calculate_financial_indicators(cf, tma_anual=0.12)["mtir_anual"] == pytest.approx(a["mtir_anual"])


# ---------------- distribuição das parcelas ----------------

def test_a_vista_cai_no_mes_da_venda():
    assert dict(inj.distribuir_venda_no_ano(100.0, 3, [{"nome": "A VISTA", "perc": 100}])) == {3: 100.0}


def test_60x_e_lido_como_60_parcelas_a_partir_do_mes_seguinte():
    m = inj.distribuir_venda_no_ano(6000.0, 10, [{"nome": "60x", "perc": 100}])
    assert dict(m) == {11: pytest.approx(100.0), 12: pytest.approx(100.0)}  # o resto é de anos seguintes


def test_entrada_mais_parcelas_como_no_motor():
    # 20% de entrada em 2 vezes (mês da venda e seguinte); 80% em 10 parcelas depois da entrada
    m = inj.distribuir_venda_no_ano(1000.0, 1, [{"nome": "12X", "perc": 100, "perc_entrada": 20, "parcelas_entrada": 2}])
    assert m[1] == pytest.approx(100.0) and m[2] == pytest.approx(100.0)
    assert m[3] == pytest.approx(80.0) and m[12] == pytest.approx(80.0)
    assert sum(m.values()) == pytest.approx(1000.0)


# ---------------- injeção ----------------

@pytest.fixture
def cenario(db_session):
    db = db_session
    plano = FinancialPlan(id=9301, db_id="1010101", name="Receita de Venda de Lotes", tp_conta="R")
    outro = CostCenter(id=9202, nome="CC de outro departamento", id_sienge="92020")
    cc = CostCenter(id=9201, nome="Loteamento Z", id_sienge="92010")
    pp = PaymentPlan(id=9401, nome="Plano 60x teste", condicoes_json=[{"nome": "60x", "perc": 100}])
    db.add_all([plano, cc, outro, pp])
    db.flush()
    db.add(DepartamentoCostCenter(departamento_id=1, cost_center_id=cc.id, permitido=True))
    fv = Forecast(id=9501, descricao="Forecast teste", ano=2026, tipo="VENDAS", departamento_id=1)
    db.add(fv)
    db.flush()
    db.add(ForecastVendaItem(forecast_id=fv.id, produto_id=cc.id, plano_venda_id=pp.id, mes=11, numero_vendas=1, ticket_medio=6000, vgv=6000))
    cat = "Receita de Venda de Lotes"
    linhas = [
        ("INC-1", cc.id, date(2026, 5, 10), 1000.0, False, cat),          # realizado: entra
        ("SP-MIG-1", cc.id, date(2026, 5, 10), 1000.0, False, cat),       # SharePoint: fora (dobraria)
        ("INC-2", cc.id, date(2026, 5, 11), 500.0, False, "Rendimentos"), # outra categoria: fora
        ("FCST-INC-1-1", cc.id, date(2026, 12, 5), 300.0, True, cat),     # em aberto futuro: entra
        ("FCST-INC-1-0", cc.id, date(2026, 9, 5), 300.0, True, cat),      # em aberto vencido: fora
        ("INC-3", outro.id, date(2026, 5, 10), 9999.0, False, cat),       # outro departamento: fora
    ]
    for sid, ccid, dt, val, fc, c in linhas:
        db.add(ActualTransaction(source_id=sid, cost_center_id=ccid, transaction_date=dt, value=val,
                                 is_forecast=fc, category=c, transaction_type="INCOME"))
    db.flush()
    return db, fv, cc, plano


def _linha_auto(db, plano, cc):
    return db.query(ForecastItem).filter(ForecastItem.plano_financeiro_id == plano.id, ForecastItem.produto_id == cc.id).all()


def test_injecao_grava_realizado_em_aberto_e_vendas_novas(cenario):
    db, fv, cc, plano = cenario
    resumo = inj.injetar_vendas_em_receitas(fv, db, hoje=HOJE)
    assert resumo["plano"] == "1010101"
    (item,) = _linha_auto(db, plano, cc)
    assert item.is_auto_generated
    assert item.mai == pytest.approx(1000.0)      # só INC-1
    assert item.set == pytest.approx(0.0)         # parcela vencida não conta
    assert item.dez == pytest.approx(300.0 + 100.0)  # em aberto + 1ª parcela do 60x
    assert item.total_anual == pytest.approx(1000.0 + 300.0 + 100.0)


def test_injecao_respeita_linha_manual_e_e_idempotente(cenario):
    db, fv, cc, plano = cenario
    inj.injetar_vendas_em_receitas(fv, db, hoje=HOJE)
    inj.injetar_vendas_em_receitas(fv, db, hoje=HOJE)
    assert len(_linha_auto(db, plano, cc)) == 1
    item = _linha_auto(db, plano, cc)[0]
    item.is_auto_generated = False
    item.jan = 7.0
    db.flush()
    inj.injetar_vendas_em_receitas(fv, db, hoje=HOJE)
    (manual,) = _linha_auto(db, plano, cc)
    assert manual.jan == 7.0 and not manual.is_auto_generated


def test_sem_plano_de_venda_de_lotes_nao_faz_nada(db_session):
    fv = Forecast(id=9601, descricao="F", ano=2026, tipo="VENDAS", departamento_id=1)
    db_session.add(fv)
    db_session.flush()
    if inj.plano_receita_venda_lotes(db_session) is None:
        assert inj.injetar_vendas_em_receitas(fv, db_session)["linhas"] == 0


def test_venda_de_mes_passado_nao_e_projetada_de_novo(cenario):
    db, fv, cc, plano = cenario
    pp = db.query(PaymentPlan).get(9401)
    # venda de maio já está no Sienge (INC/FCST-INC); projetá-la de novo contaria em dobro
    db.add(ForecastVendaItem(forecast_id=fv.id, produto_id=cc.id, plano_venda_id=pp.id, mes=5, numero_vendas=1, ticket_medio=600, vgv=600))
    db.flush()
    inj.injetar_vendas_em_receitas(fv, db, hoje=HOJE)
    (item,) = _linha_auto(db, plano, cc)
    assert item.jun == pytest.approx(0.0)
    assert item.total_anual == pytest.approx(1000.0 + 300.0 + 100.0)


def test_rentabilidade_sem_receita_relevante_vira_traco():
    assert tr._rentabilidade(-500_000.0, 58.0) is None
    assert tr._rentabilidade(100.0, 0.0) is None
    assert tr._rentabilidade(50_000.0, 200_000.0) == pytest.approx(25.0)
