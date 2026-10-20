from collections import defaultdict
from datetime import date

from app.api.routes.tracking import (
    _kpis_da_fatia,
    _kpis_do_consolidado,
    _projetar_vgv_estoque_no_fluxo,
)


def _projetar_mes_a_mes(estoque_atual, avg_vendas, avg_vgv, weights, proj_month, proj_year, max_months=600):
    anual = defaultdict(lambda: {"Entradas": 0.0})
    monthly = defaultdict(float)
    estoque_restante = float(estoque_atual)
    months = 0
    while estoque_restante > 0 and months < max_months:
        vendas_do_mes = min(avg_vendas, estoque_restante)
        estoque_restante -= vendas_do_mes
        vgv_do_mes = vendas_do_mes * avg_vgv
        for inst, weight in weights.items():
            parcela = (vgv_do_mes * weight) / inst
            if parcela > 0:
                for i in range(int(inst)):
                    m = proj_month + i
                    y = proj_year + (m - 1) // 12
                    real_m = (m - 1) % 12 + 1
                    anual[str(y)]["Entradas"] += parcela
                    monthly[f"{y}-{real_m:02d}"] += parcela
        proj_month += 1
        if proj_month > 12:
            proj_month = 1
            proj_year += 1
        months += 1
    return anual, monthly


def test_projecao_de_estoque_bate_com_o_lancamento_mes_a_mes():
    weights = {1: 0.2, 12: 0.5, 36: 0.3}
    esperado_ano, esperado_mes = _projetar_mes_a_mes(139, 4.5, 80000.0, weights, 11, 2026)
    anual = defaultdict(lambda: {"Entradas": 0.0})
    monthly = defaultdict(float)
    _projetar_vgv_estoque_no_fluxo(anual, monthly, 139, 4.5, 80000.0, weights, 11, 2026)
    assert set(monthly) == set(esperado_mes)
    for mes, valor in esperado_mes.items():
        assert monthly[mes] == pytest_approx(valor)
    for ano, row in esperado_ano.items():
        assert anual[ano]["Entradas"] == pytest_approx(row["Entradas"])


def pytest_approx(valor):
    class _Cmp:
        def __eq__(self, other):
            return abs(other - valor) <= max(1e-4, abs(valor) * 1e-9)
    return _Cmp()


def test_kpis_do_grupo_somam_vgv_vendido_e_estoque():
    kpis = _kpis_do_consolidado([
        {"vgv_vendido": 1000.0, "vgv_estoque": 400.0, "distratos": 100.0, "lucro_liq_operacional": 50.0, "final_cf_dict": {"2026-01": -10.0, "2026-02": 30.0}},
        {"vgv_vendido": 500.0, "vgv_estoque": 0.0, "distratos": 0.0, "lucro_liq_operacional": 20.0, "final_cf_dict": {"2026-02": 5.0}},
    ])
    assert kpis["vendas_acumuladas"] == 1400.0
    assert kpis["vgv_total"] == 1800.0
    assert kpis["lucro"] == 70.0
    assert kpis["perc_vendido"] == (1400.0 / 1800.0) * 100


def test_kpis_da_fatia_usam_os_campos_do_rateio():
    kpis = _kpis_da_fatia({
        "vgv_vendido": 200.0,
        "distratos": 50.0,
        "vgv_estoque": 25.0,
        "lucro_liq_operacional": 80.0,
        "tir_anual": 12.5,
        "mtir_anual": 9.0,
        "payback": 14,
        "exposicao_maxima": -30.0,
    })
    assert kpis["vendas_acumuladas"] == 150.0
    assert kpis["vgv_total"] == 175.0
    assert kpis["lucro"] == 80.0
    assert kpis["tir_anual"] == 12.5
    assert kpis["payback"] == 14


def test_lista_usa_venda_enxuta_sem_consultar_unidade():
    from datetime import date

    from app.api.routes.tracking import _VendaLista, _calc_actuals_for_cc, _kpis_do_consolidado

    prefetched = {
        "sales": {
            7: [_VendaLista(date(2026, 8, 1), 1500.0, "VGV Vendido", 12, 50.0)],
            8: [_VendaLista(date(2026, 7, 1), 500.0, "VGV Vendido", 6, 20.0)],
        },
        "real": {},
        "fcst": {},
        "units": {},
        "ccs": {},
    }
    act7 = _calc_actuals_for_cc(None, 7, cached_cat_to_group={}, prefetched=prefetched, kpis_only=True)
    act8 = _calc_actuals_for_cc(None, 8, cached_cat_to_group={}, prefetched=prefetched, kpis_only=True)
    assert act7["vgv_vendido"] == 1500.0
    assert act8["vgv_vendido"] == 500.0
    kpis = _kpis_do_consolidado([act7, act8])
    assert kpis["vendas_acumuladas"] == 2000.0
    assert kpis["vgv_total"] == 2000.0


def test_prefetch_da_lista_pode_omitir_previsto():
    import inspect
    from app.api.routes.tracking import _prefetch_tracking_actuals

    sig = inspect.signature(_prefetch_tracking_actuals)
    assert "include_forecast" in sig.parameters
    assert sig.parameters["include_forecast"].default is True


def test_calculo_do_centro_le_venda_com_data():
    import importlib
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.database import Base
    from app.models.actual_transaction import ActualTransaction
    from app.api.routes.tracking import _calc_actuals_for_cc

    for name in os.listdir("app/models"):
        if name.endswith(".py"):
            importlib.import_module("app.models." + name[:-3])

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(ActualTransaction(
        cost_center_id=7,
        source_id="s1",
        transaction_type="SALE",
        category="VGV Vendido",
        transaction_date=date(2026, 8, 1),
        value=1500.0,
        is_forecast=False,
    ))
    db.commit()
    act = _calc_actuals_for_cc(db, 7, cached_cat_to_group={})
    assert act["vgv_vendido"] == 1500.0


def test_mesmo_produto_obra_inclui_sufixo_e_nao_mistura_ii():
    from types import SimpleNamespace
    from app.api.routes.tracking import _mesmo_produto_obra, parse_project_name

    def nome(texto):
        return parse_project_name(SimpleNamespace(nome=texto, custom_data={}))[1]

    central = nome("AVARÉ - CENTRAL PARQUE II")
    assert _mesmo_produto_obra(central, nome("AVARÉ - CENTRAL PARQUE II - OBRAS"))
    assert _mesmo_produto_obra(central, nome("AVARÉ - CENTRAL PARQUE II - PARCERIA"))
    assert _mesmo_produto_obra(central, nome("AVARÉ - CENTRAL PARQUE II - MARKETING"))
    assert not _mesmo_produto_obra(central, nome("AVARÉ - RESERVA CENTRAL PARQUE II"))
    assert not _mesmo_produto_obra(nome("AVARÉ - RESERVA CENTRAL PARQUE"), nome("AVARÉ - RESERVA CENTRAL PARQUE II"))


def test_mesmo_produto_obra_separa_as_duas_obras_do_prefixo_143():
    from types import SimpleNamespace
    from app.api.routes.tracking import _mesmo_produto_obra, parse_project_name

    def nome(texto):
        return parse_project_name(SimpleNamespace(nome=texto, custom_data={}))[1]

    morada = nome("BOITUVA - MORADA DOS IPÊS II")
    reserva = nome("BOITUVA - RESERVA DOS IPÊS")
    membros_morada = [
        "BOITUVA - MORADA DOS IPÊS II",
        "BOITUVA - MORADA DOS IPÊS II - OBRAS",
    ]
    membros_reserva = [
        "BOITUVA - RESERVA DOS IPÊS",
        "BOITUVA - RESERVA DOS IPÊS - OBRAS",
        "BOITUVA - RESERVA DOS IPÊS - MLDU (ELLENCO & MLDU)",
        "BOITUVA - RESERVA DOS IPÊS - MLDU (VERCELLINO)",
    ]
    for texto in membros_morada:
        assert _mesmo_produto_obra(morada, nome(texto)), texto
        assert not _mesmo_produto_obra(reserva, nome(texto)), texto
    for texto in membros_reserva:
        assert _mesmo_produto_obra(reserva, nome(texto)), texto
        assert not _mesmo_produto_obra(morada, nome(texto)), texto
