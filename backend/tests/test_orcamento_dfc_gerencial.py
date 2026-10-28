"""DFC gerencial: fatia os mesmos números do DFC por empresa e CC.

Não testa fórmula de orçado/realizado — só conferência com montar_dfc e o corte MLDU.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.orcamento_dfc import MESES_STR, montar_dfc
from app.services.orcamento_dfc_gerencial import AGRUPAMENTO_CENTRO, montar_dfc_gerencial


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


def _opcoes():
    return [
        {"id": 1, "nome": "CC Alpha", "id_empresa": "10", "nome_empresa": "SPE Alpha"},
        {"id": 2, "nome": "CC Beta", "id_empresa": "10", "nome_empresa": "SPE Alpha"},
        {"id": 3, "nome": "CC Gama", "id_empresa": "20", "nome_empresa": "SPE Gama"},
    ]


def _base():
    rec_n = [
        _item(10, 1, realizado={"jan": 100.0}, orcado={"jan": 90.0}, forecast={"jan": 95.0}),
        _item(10, 3, realizado={"jan": 50.0}, orcado={"jan": 40.0}, forecast={"jan": 45.0}),
        _item(99, 1, realizado={"jan": 999.0}),
    ]
    desp_n = [
        _item(20, 1, realizado={"jan": 40.0}, orcado={"jan": 50.0}, forecast={"jan": 45.0}),
        _item(20, 2, realizado={"jan": 10.0}, orcado={"jan": 8.0}, forecast={"jan": 9.0}),
    ]
    rec_n1 = [
        _item(10, 1, realizado={"jan": 80.0}, orcado={"jan": 999.0}),
        _item(10, 3, realizado={"jan": 20.0}),
    ]
    desp_n1 = [
        _item(20, 1, realizado={"jan": 30.0}),
        _item(20, 2, realizado={"jan": 5.0}),
    ]
    return rec_n, desp_n, rec_n1, desp_n1


class TestConferenciaComDfc:
    def test_liquido_cheio_bate_com_dfc(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        dfc = montar_dfc(_nodes(), rec_n, desp_n, rec_n1, desp_n1)
        ger = montar_dfc_gerencial(
            _nodes(),
            rec_n,
            desp_n,
            rec_n,
            desp_n,
            rec_n1,
            desp_n1,
            rec_n1,
            desp_n1,
            _opcoes(),
        )
        assert ger["liquido"] == dfc["liquido"]
        assert ger["liquido_n1"] == dfc["liquido_n1"]
        assert ger["liquido_orcado"] == dfc["liquido_orcado"]
        assert ger["liquido_forecast"] == dfc["liquido_forecast"]
        assert ger["total_entradas"] == dfc["total_entradas"]
        assert ger["liquido"] == 100.0  # 150 rec - 50 desp

    def test_plano_fora_da_visao_nao_entra(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        ger = montar_dfc_gerencial(
            _nodes(), rec_n, desp_n, rec_n, desp_n, rec_n1, desp_n1, rec_n1, desp_n1, _opcoes()
        )
        blob = str(ger)
        assert "999" not in blob or "plano_financeiro_id" not in blob
        assert ger["total_entradas"] == 150.0

    def test_n1_ignora_orcado_do_ano_anterior(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        ger = montar_dfc_gerencial(
            _nodes(), rec_n, desp_n, rec_n, desp_n, rec_n1, desp_n1, rec_n1, desp_n1, _opcoes()
        )
        assert ger["liquido_n1"] == 65.0  # 100 rec - 35 desp; orçado 999 não entra

    def test_mldu_nao_altera_cheio(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        ger = montar_dfc_gerencial(
            _nodes(),
            rec_n,
            desp_n,
            _scale(rec_n, 0.5),
            _scale(desp_n, 0.5),
            rec_n1,
            desp_n1,
            _scale(rec_n1, 0.5),
            _scale(desp_n1, 0.5),
            _opcoes(),
        )
        assert ger["liquido"] == 100.0
        assert ger["liquido_real_mldu"] == 50.0
        assert ger["liquido_n1"] == 65.0
        assert ger["liquido_n1_mldu"] == 32.5


class TestAgrupamento:
    def test_empresa_visao_plano_cc(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        ger = montar_dfc_gerencial(
            _nodes(), rec_n, desp_n, rec_n, desp_n, rec_n1, desp_n1, rec_n1, desp_n1, _opcoes()
        )
        nomes = [e["descricao"] for e in ger["empresas"]]
        assert nomes == ["SPE Alpha", "SPE Gama"]
        alpha = ger["empresas"][0]
        cats = {c["codigo"]: c for c in alpha["filhos"]}
        receitas = cats["01.01"]
        assert receitas["kind"] == "categoria"
        plano = receitas["filhos"][0]
        assert plano["kind"] == "plano"
        assert plano["descricao"] == "Vendas"
        centros = {c["descricao"]: c for c in plano["filhos"]}
        assert centros["CC Alpha"]["total_real"] == 100.0
        assert "CC Beta" not in centros
        saidas = cats["02.01"]
        cc_desp = {c["descricao"] for c in saidas["filhos"][0]["filhos"]}
        assert cc_desp == {"CC Alpha", "CC Beta"}
        assert alpha["total_real"] == 50.0  # 100 - 40 - 10
        gama = ger["empresas"][1]
        assert gama["total_real"] == 50.0

    def test_empresa_cc_visao_plano(self):
        rec_n, desp_n, rec_n1, desp_n1 = _base()
        ger = montar_dfc_gerencial(
            _nodes(),
            rec_n,
            desp_n,
            rec_n,
            desp_n,
            rec_n1,
            desp_n1,
            rec_n1,
            desp_n1,
            _opcoes(),
            agrupamento=AGRUPAMENTO_CENTRO,
        )
        alpha = ger["empresas"][0]
        assert {c["kind"] for c in alpha["filhos"]} == {"centro"}
        nomes = [c["descricao"] for c in alpha["filhos"]]
        assert nomes == ["CC Alpha", "CC Beta"]
        alpha_cc = next(c for c in alpha["filhos"] if c["descricao"] == "CC Alpha")
        cats = {c["codigo"]: c for c in alpha_cc["filhos"]}
        plano = cats["01.01"]["filhos"][0]
        assert plano["kind"] == "plano"
        assert plano["filhos"] == []
        assert plano["total_real"] == 100.0
        assert ger["liquido"] == 100.0

    def test_filtro_de_meses_afeta_total_nao_a_grade(self):
        rec_n = [_item(10, 1, realizado={"jan": 100.0, "fev": 50.0})]
        rec_n1 = [_item(10, 1, realizado={"jan": 40.0, "fev": 10.0})]
        ger = montar_dfc_gerencial(
            _nodes(), rec_n, [], rec_n, [], rec_n1, [], rec_n1, [], _opcoes(), meses=["jan"]
        )
        rec = next(
            c
            for e in ger["empresas"]
            for c in e["filhos"]
            if c["codigo"] == "01.01"
        )
        assert rec["meses_real"]["fev"] == 50.0
        assert rec["total_real"] == 100.0
        assert rec["total_n1"] == 40.0
