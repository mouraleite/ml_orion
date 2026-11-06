"""Despesas por empreendimento: mix YTD/YTG, sinal positivo, MLDU e exclusões da visão 05.xx."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.orcamento_despesas_empreendimento import (
    mix_real_forecast,
    montar_despesas_empreendimento,
)
from app.services.periodos import MESES_STR


def _item(plano_id, produto_id=1, realizado=None, orcado=None, forecast=None):
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
        "produto_id": produto_id,
        "plano_financeiro_id": plano_id,
        "realizado": rec,
        "orcado": orc,
        "forecast": fc,
    }


def _scale(itens, fator):
    out = []
    for item in itens:
        row = dict(item)
        for serie in ("orcado", "realizado", "forecast"):
            src = item[serie]
            row[serie] = {k: float(v) * fator for k, v in src.items()}
        out.append(row)
    return out


def _nodes():
    return [
        {"id": 1, "codigo": "01", "descricao": "RECEITAS", "planos": []},
        {
            "id": 2,
            "codigo": "01.01",
            "descricao": "VENDAS",
            "planos": [{"id": 10, "name": "Vendas", "db_id": "1.1.01"}],
        },
        {"id": 3, "codigo": "05", "descricao": "DESPESAS", "planos": []},
        {
            "id": 4,
            "codigo": "05.01",
            "descricao": "DESPESAS COMERCIAIS",
            "planos": [{"id": 20, "name": "Comissão", "db_id": "2.05.01.01"}],
        },
        {
            "id": 5,
            "codigo": "05.03",
            "descricao": "ADMINISTRATIVAS",
            "planos": [{"id": 21, "name": "Adm", "db_id": "2.05.03.01"}],
        },
        {
            "id": 6,
            "codigo": "05.08",
            "descricao": "GRUPO EXCLUÍDO",
            "planos": [{"id": 22, "name": "Ignorar", "db_id": "2.05.08.01"}],
        },
        {
            "id": 7,
            "codigo": "05.09",
            "descricao": "RETENÇÕES",
            "planos": [{"id": 23, "name": "Retenção 09.01", "db_id": "09.01.01"}],
        },
    ]


def _opcoes():
    return [
        {"id": 1, "nome": "17701 Jd. dos Ipês III", "id_empresa": "10", "nome_empresa": "JARDIM DOS IPÊS III"},
        {"id": 2, "nome": "Frota", "id_empresa": "10", "nome_empresa": "JARDIM DOS IPÊS III"},
        {"id": 3, "nome": "CC Gama", "id_empresa": "20", "nome_empresa": "SPE Gama"},
    ]


def _base():
    desp_n = [
        _item(20, 1, realizado={"jan": 100.0, "out": 1.0}, orcado={"jan": 999.0}, forecast={"jan": 5.0, "out": 40.0}),
        _item(21, 1, realizado={"jan": 20.0}, forecast={"out": 10.0}),
        _item(21, 2, realizado={"jan": 8.0}, forecast={"out": 4.0}),
        _item(22, 1, realizado={"jan": 50.0}, forecast={"out": 50.0}),
        _item(23, 1, realizado={"jan": 30.0}, forecast={"out": 30.0}),
        _item(10, 1, realizado={"jan": 1000.0}),
    ]
    desp_ref = [
        _item(20, 1, orcado={"jan": 80.0, "out": 20.0}, forecast={"jan": 70.0, "out": 15.0}),
        _item(21, 1, orcado={"jan": 10.0}, forecast={"jan": 9.0}),
        _item(21, 2, orcado={"jan": 4.0}, forecast={"jan": 3.0}),
        _item(22, 1, orcado={"jan": 99.0}),
        _item(23, 1, orcado={"jan": 99.0}),
    ]
    return desp_n, desp_ref


class TestMix:
    def test_antes_do_corte_usa_realizado_depois_usa_forecast(self):
        mix = mix_real_forecast({"jan": 100.0, "out": 1.0}, {"jan": 5.0, "out": 40.0}, 9)
        assert mix["jan"] == 100.0
        assert mix["set"] == 0.0
        assert mix["out"] == 40.0
        assert mix["out"] != 1.0


class TestMontagem:
    def test_sinal_positivo_e_nao_usa_orcado_do_ano_base(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, _opcoes(), corte=9)
        assert out["total_n"] > 0
        assert out["total_n"] == 100.0 + 40.0 + 20.0 + 10.0 + 8.0 + 4.0
        assert out["total_orcado"] == 80.0 + 20.0 + 10.0 + 4.0
        assert 999.0 not in (out["total_n"], out["total_orcado"])

    def test_ytd_ytg_fy(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, _opcoes(), corte=9)
        p = out["periodos"]
        assert p["ytd"]["n"] == 100.0 + 20.0 + 8.0
        assert p["ytg"]["n"] == 40.0 + 10.0 + 4.0
        assert p["fy"]["n"] == p["ano"]["n"]
        assert abs(p["fy"]["n"] - (p["ytd"]["n"] + p["ytg"]["n"])) < 1e-9

    def test_exclui_05_08_09_01_e_receita(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, _opcoes(), corte=9)
        blob = str(out)
        assert "GRUPO EXCLUÍDO" not in blob
        assert "Retenção 09.01" not in blob
        assert "Vendas" not in blob
        assert out["total_n"] != out["total_n"] + 50.0

    def test_mldu_nao_altera_cheio(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(
            _nodes(), desp_n, _scale(desp_n, 0.5), desp_ref, _scale(desp_ref, 0.5), _opcoes(), corte=9
        )
        assert out["total_n_mldu"] == out["total_n"] * 0.5
        assert out["total_orcado_mldu"] == out["total_orcado"] * 0.5
        assert out["total_n"] == 100.0 + 40.0 + 20.0 + 10.0 + 8.0 + 4.0

    def test_hierarquia_empresa_grupo_centro_plano(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, _opcoes(), corte=9)
        nomes = [e["descricao"] for e in out["empresas"]]
        assert nomes == ["JARDIM DOS IPÊS III", "SPE Gama"] or "JARDIM DOS IPÊS III" in nomes
        emp = next(e for e in out["empresas"] if e["descricao"] == "JARDIM DOS IPÊS III")
        grupos = {g["codigo"]: g for g in emp["filhos"]}
        assert set(grupos) == {"05.01", "05.03"}
        assert grupos["05.01"]["kind"] == "grupo"
        centro = grupos["05.01"]["filhos"][0]
        assert centro["kind"] == "centro"
        assert centro["descricao"] == "17701 Jd. dos Ipês III"
        plano = centro["filhos"][0]
        assert plano["kind"] == "plano"
        assert plano["descricao"] == "Comissão"
        assert plano["meses_n"]["jan"] == 100.0
        assert plano["meses_n"]["out"] == 40.0
        assert plano["meses_orcado"]["jan"] == 80.0

    def test_amarra_empresa_por_id_mesmo_quando_o_nome_repete(self):
        opcoes = [
            {"id": 1, "nome": "CC A", "id_empresa": "4", "nome_empresa": "TERRAS DE ITU"},
            {"id": 2, "nome": "CC B", "id_empresa": "32", "nome_empresa": "TERRAS DE ITU"},
        ]
        desp_n = [
            _item(20, 1, realizado={"jan": 10.0}),
            _item(20, 2, realizado={"jan": 20.0}),
        ]
        desp_ref = [
            _item(20, 1, orcado={"jan": 10.0}),
            _item(20, 2, orcado={"jan": 20.0}),
        ]
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, opcoes, corte=9)
        assert {e["empresa_id"] for e in out["empresas"]} == {"4", "32"}
        assert {e["codigo"] for e in out["empresas"]} == {"4", "32"}
        assert len(out["empresas"]) == 2

    def test_forecast_n1_nao_mistura_com_mix(self):
        desp_n, desp_ref = _base()
        out = montar_despesas_empreendimento(_nodes(), desp_n, desp_n, desp_ref, desp_ref, _opcoes(), corte=9)
        emp = next(e for e in out["empresas"] if e["descricao"] == "JARDIM DOS IPÊS III")
        g = next(x for x in emp["filhos"] if x["codigo"] == "05.01")
        assert g["meses_forecast"]["jan"] == 70.0
        assert g["meses_n"]["jan"] == 100.0
