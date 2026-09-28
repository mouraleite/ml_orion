"""DFC do orçamento: agrupa números já calculados pela Visão DFC.

Não testa fórmula de orçado/realizado — só agrupamento, sinal, AH e AV.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.orcamento_dfc import (
    MESES_STR,
    montar_dfc,
    montar_dfc_comparativo,
    par_ids_forecast_dfc,
    ratio_ah,
    ratio_av,
)


def _item(plano_id: int, realizado=None, orcado=None, forecast=None):
    rec = {m: 0.0 for m in MESES_STR}
    orc = {m: 0.0 for m in MESES_STR}
    fc = {m: 0.0 for m in MESES_STR}
    if realizado:
        rec.update(realizado)
    if orcado:
        orc.update(orcado)
    if forecast:
        fc.update(forecast)
    rec["total"] = sum(rec[m] for m in MESES_STR)
    orc["total"] = sum(orc[m] for m in MESES_STR)
    fc["total"] = sum(fc[m] for m in MESES_STR)
    return {
        "produto_id": 1,
        "plano_financeiro_id": plano_id,
        "realizado": rec,
        "orcado": orc,
        "forecast": fc,
    }


def _nodes():
    return [
        {"id": 1, "codigo": "01", "descricao": "ENTRADAS", "planos": []},
        {
            "id": 2,
            "codigo": "01.01",
            "descricao": "Receitas",
            "planos": [{"id": 10, "name": "Vendas", "db_id": "1.1.01"}],
        },
        {"id": 3, "codigo": "02", "descricao": "SAIDAS", "planos": []},
        {
            "id": 4,
            "codigo": "02.01",
            "descricao": "Despesas",
            "planos": [{"id": 20, "name": "Obra", "db_id": "2.1.01"}],
        },
    ]


class TestRatios:
    def test_ah_vs_ano_anterior(self):
        assert abs(ratio_ah(120.0, 100.0) - 0.20) < 1e-12

    def test_ah_base_zero(self):
        assert ratio_ah(50.0, 0.0) is None

    def test_ah_usa_modulo_da_base(self):
        assert abs(ratio_ah(-80.0, -100.0) - 0.20) < 1e-12

    def test_av_linha_sobre_entradas(self):
        assert abs(ratio_av(25.0, 100.0) - 0.25) < 1e-12

    def test_av_ancora_zero(self):
        assert ratio_av(10.0, 0.0) is None


class TestMontarDfc:
    def test_saida_fica_negativa_e_nao_mapeado_some(self):
        payload = montar_dfc(
            nodes=_nodes(),
            rec_n=[
                _item(10, realizado={"jan": 100.0}, orcado={"jan": 90.0}),
                _item(99, realizado={"jan": 999.0}),
            ],
            desp_n=[_item(20, realizado={"jan": 40.0}, orcado={"jan": 50.0})],
            rec_n1=[_item(10, realizado={"jan": 80.0})],
            desp_n1=[_item(20, realizado={"jan": 30.0})],
        )
        by_codigo = {n["codigo"]: n for n in payload["linhas"]}

        assert 99 not in {
            p["id"] for n in payload["linhas"] for p in n.get("planos", [])
        }
        assert by_codigo["01.01"]["meses"]["jan"] == 100.0
        assert by_codigo["02.01"]["meses"]["jan"] == -40.0
        assert by_codigo["01"]["meses"]["jan"] == 100.0
        assert by_codigo["02"]["meses"]["jan"] == -40.0

    def test_ah_av_no_total_do_ano(self):
        payload = montar_dfc(
            nodes=_nodes(),
            rec_n=[_item(10, realizado={"jan": 100.0, "fev": 50.0}, orcado={"jan": 200.0})],
            desp_n=[_item(20, realizado={"jan": 30.0})],
            rec_n1=[_item(10, realizado={"jan": 100.0})],
            desp_n1=[_item(20, realizado={"jan": 20.0})],
        )
        rec = next(n for n in payload["linhas"] if n["codigo"] == "01.01")
        desp = next(n for n in payload["linhas"] if n["codigo"] == "02.01")

        assert rec["total"] == 150.0
        assert rec["total_n1"] == 100.0
        assert rec["total_orcado"] == 200.0
        assert abs(rec["ah"] - 0.50) < 1e-12
        assert abs(rec["av"] - 1.0) < 1e-12
        assert payload["total_entradas"] == 150.0
        assert abs(desp["av"] - (-30.0 / 150.0)) < 1e-12

    def test_filtro_de_meses_afeta_total_nao_a_grade(self):
        payload = montar_dfc(
            nodes=_nodes(),
            rec_n=[_item(10, realizado={"jan": 100.0, "fev": 50.0})],
            desp_n=[],
            rec_n1=[_item(10, realizado={"jan": 40.0, "fev": 10.0})],
            desp_n1=[],
            meses=["jan"],
        )
        rec = next(n for n in payload["linhas"] if n["codigo"] == "01.01")
        assert rec["meses"]["fev"] == 50.0
        assert rec["total"] == 100.0
        assert rec["total_n1"] == 40.0
        assert abs(rec["ah"] - 1.5) < 1e-12

    def test_meses_trazem_real_n1_orcado_e_forecast(self):
        payload = montar_dfc(
            nodes=_nodes(),
            rec_n=[_item(10, realizado={"jan": 100.0}, orcado={"jan": 90.0}, forecast={"jan": 95.0})],
            desp_n=[_item(20, realizado={"jan": 40.0}, orcado={"jan": 50.0}, forecast={"jan": 45.0})],
            rec_n1=[_item(10, realizado={"jan": 80.0})],
            desp_n1=[_item(20, realizado={"jan": 30.0})],
        )
        rec = next(n for n in payload["linhas"] if n["codigo"] == "01.01")
        desp = next(n for n in payload["linhas"] if n["codigo"] == "02.01")
        assert rec["meses"]["jan"] == 100.0
        assert rec["meses_n1"]["jan"] == 80.0
        assert rec["meses_orcado"]["jan"] == 90.0
        assert rec["meses_forecast"]["jan"] == 95.0
        assert desp["meses"]["jan"] == -40.0
        assert desp["meses_n1"]["jan"] == -30.0
        assert desp["meses_orcado"]["jan"] == -50.0
        assert desp["meses_forecast"]["jan"] == -45.0
        assert payload["liquido_forecast"] == 50.0

    def test_ah_av_mensal_usa_real_e_entradas_do_mes(self):
        payload = montar_dfc(
            nodes=_nodes(),
            rec_n=[_item(10, realizado={"jan": 100.0, "fev": 50.0})],
            desp_n=[_item(20, realizado={"jan": 30.0})],
            rec_n1=[_item(10, realizado={"jan": 80.0, "fev": 50.0})],
            desp_n1=[_item(20, realizado={"jan": 20.0})],
        )
        rec = next(n for n in payload["linhas"] if n["codigo"] == "01.01")
        desp = next(n for n in payload["linhas"] if n["codigo"] == "02.01")
        assert abs(rec["meses_ah"]["jan"] - 0.25) < 1e-12
        assert rec["meses_ah"]["fev"] == 0.0
        assert rec["meses_ah"]["mar"] is None
        assert abs(rec["meses_av"]["jan"] - 1.0) < 1e-12
        assert abs(rec["meses_av"]["fev"] - 1.0) < 1e-12
        assert abs(desp["meses_av"]["jan"] - (-30.0 / 100.0)) < 1e-12
        assert abs(payload["total_entradas_meses"]["jan"] - 100.0) < 1e-12


def _fc(fid, tipo, descricao="Forecast - 7+5", dept=18):
    return {"id": fid, "tipo": tipo, "descricao": descricao, "departamento_id": dept}


class TestParIdsForecastDfc:
    """O acompanhamento só aceita id do próprio tipo; o DFC resolve o par pela descrição."""

    _pares = [_fc(43, "VENDAS"), _fc(123, "DESPESAS"), _fc(124, "RECEITAS")]

    def test_vendas_7_mais_5_puxa_despesas_e_receitas(self):
        assert par_ids_forecast_dfc(43, _fc(43, "VENDAS"), self._pares, 18) == (123, 124)

    def test_despesas_puxa_receitas_irma(self):
        assert par_ids_forecast_dfc(123, _fc(123, "DESPESAS"), self._pares, 18) == (123, 124)

    def test_receitas_puxa_despesas_irma(self):
        assert par_ids_forecast_dfc(124, _fc(124, "RECEITAS"), self._pares, 18) == (123, 124)

    def test_sem_versao_nao_forca_id(self):
        assert par_ids_forecast_dfc(None, None, self._pares, 18) == (None, None)

    def test_prefere_mesmo_departamento(self):
        pares = [
            _fc(123, "DESPESAS", dept=18),
            _fc(200, "DESPESAS", dept=1),
            _fc(124, "RECEITAS", dept=18),
        ]
        assert par_ids_forecast_dfc(43, _fc(43, "VENDAS", dept=18), pares, 18) == (123, 124)


def _viz_item(plano_id: int, **meses):
    row = {m: 0.0 for m in MESES_STR}
    row.update(meses)
    row["produto_id"] = 1
    row["plano_financeiro_id"] = plano_id
    row["total"] = sum(row[m] for m in MESES_STR)
    return row


class TestMontarDfcComparativo:
    def test_var_entre_versoes_com_sinal_de_saida(self):
        payload = montar_dfc_comparativo(
            nodes=_nodes(),
            rec_a=[_viz_item(10, jan=100.0)],
            desp_a=[_viz_item(20, jan=40.0)],
            rec_b=[_viz_item(10, jan=120.0)],
            desp_b=[_viz_item(20, jan=30.0)],
        )
        by_codigo = {n["codigo"]: n for n in payload["linhas"]}
        assert by_codigo["01.01"]["total_a"] == 100.0
        assert by_codigo["01.01"]["total_b"] == 120.0
        assert by_codigo["02.01"]["total_a"] == -40.0
        assert by_codigo["02.01"]["total_b"] == -30.0
        assert payload["liquido_a"] == 60.0
        assert payload["liquido_b"] == 90.0
        assert payload["var_liquido"] == 30.0
        assert abs(payload["var_liquido_perc"] - 0.5) < 1e-12
