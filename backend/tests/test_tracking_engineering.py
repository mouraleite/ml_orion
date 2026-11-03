from datetime import date


def test_aloca_so_o_saldo_nao_comprometido_a_partir_do_proximo_mes():
    from app.services.tracking_engineering import alocar_cronograma_nao_comprometido

    cronograma = {
        "2026-10": {"Obras": 200.0},
        "2026-11": {"Obras": 100.0},
        "2026-12": {"Obras": 400.0, "Despesas com Marketing": 100.0},
        "2027-01": {"Obras": 200.0},
    }
    out = alocar_cronograma_nao_comprometido(cronograma, comprometido=300.0, a_partir_de="2026-12")
    assert "2026-10" not in out
    assert "2026-11" not in out
    # total 1000 - 300 = 700; futuro 700 → fator 1
    assert out["2026-12"]["Obras"] == 400.0
    assert out["2026-12"]["Despesas com Marketing"] == 100.0
    assert out["2027-01"]["Obras"] == 200.0


def test_aloca_escala_o_futuro_quando_ainda_falta_comprometer():
    from app.services.tracking_engineering import alocar_cronograma_nao_comprometido

    cronograma = {
        "2026-11": {"Obras": 200.0},
        "2026-12": {"Obras": 400.0},
        "2027-01": {"Obras": 400.0},
    }
    out = alocar_cronograma_nao_comprometido(cronograma, comprometido=0.0, a_partir_de="2026-12")
    # remaining 1000; futuro 800 → fator 1.25 (o atraso de 200 entra no futuro)
    assert round(out["2026-12"]["Obras"], 2) == 500.0
    assert round(out["2027-01"]["Obras"], 2) == 500.0


def test_aloca_empurra_saldo_atrasado_para_os_meses_futuros():
    from app.services.tracking_engineering import alocar_cronograma_nao_comprometido

    cronograma = {
        "2026-10": {"Obras": 500.0},
        "2026-12": {"Obras": 250.0},
        "2027-01": {"Obras": 250.0},
    }
    out = alocar_cronograma_nao_comprometido(cronograma, comprometido=100.0, a_partir_de="2026-12")
    # remaining 900; futuro 500 → fator 1.8
    assert round(out["2026-12"]["Obras"], 2) == 450.0
    assert round(out["2027-01"]["Obras"], 2) == 450.0


def test_aloca_nao_inventa_gasto_se_comprometido_ja_cobre_o_orcamento():
    from app.services.tracking_engineering import alocar_cronograma_nao_comprometido

    cronograma = {"2026-12": {"Obras": 100.0}, "2027-01": {"Obras": 50.0}}
    assert alocar_cronograma_nao_comprometido(cronograma, comprometido=200.0, a_partir_de="2026-12") == {}


def test_aloca_lanca_no_proximo_mes_se_cronograma_so_tem_passado():
    from app.services.tracking_engineering import alocar_cronograma_nao_comprometido

    cronograma = {"2026-01": {"Obras": 80.0}}
    out = alocar_cronograma_nao_comprometido(cronograma, comprometido=20.0, a_partir_de="2026-12")
    assert out == {"2026-12": {"Obras": 60.0}}


def test_proximo_mes_pula_o_mes_atual():
    from app.services.tracking_engineering import proximo_mes_yyyy_mm

    assert proximo_mes_yyyy_mm(date(2026, 11, 3)) == "2026-12"
    assert proximo_mes_yyyy_mm(date(2026, 12, 31)) == "2027-01"


def test_categoria_do_sheet_nao_mistura_infra_com_funding():
    from app.services.tracking_engineering import categoria_do_sheet

    assert categoria_do_sheet("Custos Infraestrutura Implantação") == "Obras"
    assert categoria_do_sheet("Custo com Captação/ Estruturação") == "Funding"
    assert categoria_do_sheet("Despesas com Marketing") == "Despesas com Marketing"
    assert categoria_do_sheet("Despesas Comerciais") == "Despesas Comerciais"
    assert categoria_do_sheet("Custos Projetos e Regularizações") == "Projetos"


def _sqlite():
    import importlib
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.database import Base

    for name in os.listdir("app/models"):
        if name.endswith(".py"):
            importlib.import_module("app.models." + name[:-3])

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_grava_trk_eng_sem_mexer_em_op1_nem_contas_a_pagar():
    from app.models.actual_transaction import ActualTransaction
    from app.models.cost_center import CostCenter
    from app.services.tracking_engineering import persistir_cronograma_engenharia

    db = _sqlite()
    db.add(CostCenter(id=12, id_sienge="17712", nome="TAGUAI - JARDIM DOS IPÊS III - OBRAS"))
    db.add_all([
        ActualTransaction(
            cost_center_id=12, source_id="OUT-1-OP1-PMT-1-DT-20261001-FC-1",
            transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 10, 1),
            value=50.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=12, source_id="FCST-OUT-99-1",
            transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 12, 10),
            value=30.0, is_forecast=True,
        ),
    ])
    db.commit()
    persistir_cronograma_engenharia(
        db,
        building_id="17700",
        target_cc_id=12,
        alocado={"2026-12": {"Obras": 70.0}, "2027-01": {"Obras": 80.0}},
    )
    op1 = db.query(ActualTransaction).filter(ActualTransaction.source_id.like("OUT-%-OP1-%")).one()
    ap = db.query(ActualTransaction).filter(ActualTransaction.source_id == "FCST-OUT-99-1").one()
    assert op1.value == 50.0
    assert ap.value == 30.0
    eng = db.query(ActualTransaction).filter(ActualTransaction.source_id.like("TRK-ENG-%")).all()
    assert sorted((r.source_id, round(r.value, 2), r.is_forecast) for r in eng) == [
        ("TRK-ENG-17700-2026-12-obras", 70.0, True),
        ("TRK-ENG-17700-2027-01-obras", 80.0, True),
    ]


def test_reescrever_trk_eng_nao_apaga_titulo_em_aberto():
    from app.models.actual_transaction import ActualTransaction
    from app.models.cost_center import CostCenter
    from app.services.tracking_engineering import persistir_cronograma_engenharia

    db = _sqlite()
    db.add(CostCenter(id=12, id_sienge="17712", nome="OBRAS"))
    db.add(ActualTransaction(
        cost_center_id=12, source_id="FCST-OUT-1-1",
        transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 12, 1),
        value=10.0, is_forecast=True,
    ))
    db.add(ActualTransaction(
        cost_center_id=12, source_id="TRK-ENG-17700-2026-12-obras",
        transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 12, 1),
        value=999.0, is_forecast=True,
    ))
    db.commit()
    persistir_cronograma_engenharia(
        db, building_id="17700", target_cc_id=12, alocado={"2026-12": {"Obras": 5.0}},
    )
    ap = db.query(ActualTransaction).filter(ActualTransaction.source_id == "FCST-OUT-1-1").one()
    assert ap.value == 10.0
    eng = db.query(ActualTransaction).filter(ActualTransaction.source_id.like("TRK-ENG-%")).all()
    assert len(eng) == 1
    assert eng[0].value == 5.0


def test_comprometido_soma_realizado_e_ap_e_ignora_trk_eng():
    from app.models.actual_transaction import ActualTransaction
    from app.services.tracking_engineering import comprometido_obra_do_grupo

    db = _sqlite()
    db.add_all([
        ActualTransaction(
            cost_center_id=1, source_id="OUT-1-OP1-PMT-1-DT-20261001-FC-1",
            transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 10, 1),
            value=50.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=1, source_id="FCST-OUT-2-1",
            transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 12, 1),
            value=30.0, is_forecast=True,
        ),
        ActualTransaction(
            cost_center_id=1, source_id="TRK-ENG-17700-2026-12-obras",
            transaction_type="OUTCOME", category="Obras", transaction_date=date(2026, 12, 1),
            value=999.0, is_forecast=True,
        ),
        ActualTransaction(
            cost_center_id=1, source_id="FCST-INC-3-1",
            transaction_type="INCOME", category="Receita", transaction_date=date(2026, 12, 1),
            value=80.0, is_forecast=True,
        ),
    ])
    db.commit()
    assert comprometido_obra_do_grupo(db, [1]) == 80.0


def test_acompanhamento_usa_trk_eng_sem_alterar_op1():
    from app.models.actual_transaction import ActualTransaction
    from app.api.routes.tracking import _calc_actuals_for_cc, _kpis_do_consolidado

    db = _sqlite()
    db.add_all([
        ActualTransaction(
            cost_center_id=7, source_id="INC-1",
            transaction_type="INCOME", category="Receita de Venda de Lotes",
            transaction_date=date(2026, 8, 1), value=1000.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=7, source_id="OUT-1-OP1-PMT-1-DT-20260801-FC-1",
            transaction_type="OUTCOME", category="Materiais Aplicados (Obra)",
            transaction_date=date(2026, 8, 1), value=100.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=7, source_id="FCST-OUT-1",
            transaction_type="OUTCOME", category="Materiais Aplicados (Obra)",
            transaction_date=date(2026, 12, 1), value=50.0, is_forecast=True,
        ),
        ActualTransaction(
            cost_center_id=7, source_id="TRK-ENG-17700-2027-03-obras",
            transaction_type="OUTCOME", category="Obras",
            transaction_date=date(2027, 3, 1), value=2000.0, is_forecast=True,
        ),
    ])
    db.commit()
    act = _calc_actuals_for_cc(db, 7, cached_cat_to_group={})
    assert act["final_cf_dict"]["2026-08"] == 900.0
    assert act["final_cf_dict"]["2026-12"] == -50.0
    assert act["final_cf_dict"]["2027-03"] == -2000.0
    kpis = _kpis_do_consolidado([act])
    assert kpis["lucro"] == -1150.0
    assert kpis["exposicao_max_caixa"] < 0
