"""Roll-forward de geração de caixa: corte, mix YTD/YTG, cadeia e filtro B+I+C.

Não testa fórmula de orçado/realizado — só o card do DFC.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.geracao_caixa import (
    TIPOS_CAIXA,
    abertura_encadeada,
    corte_caixa,
    eh_conta_caixa,
    eh_mutuo,
    fluxo_ytd_ytg,
    ids_recorte_caixa,
    montar_bloco_geracao,
    posicao_fim_ano,
    saldo_caixa,
    serie_liquido_visao,
)
from app.services.periodos import MESES_STR


HOJE = date(2026, 11, 6)


def _item(plano_id: int, realizado=None, orcado=None):
    rec = {m: 0.0 for m in MESES_STR}
    orc = {m: 0.0 for m in MESES_STR}
    if realizado:
        rec.update(realizado)
    if orcado:
        orc.update(orcado)
    rec["total"] = sum(rec[m] for m in MESES_STR)
    orc["total"] = sum(orc[m] for m in MESES_STR)
    return {
        "produto_id": 1,
        "plano_financeiro_id": plano_id,
        "realizado": rec,
        "orcado": orc,
        "forecast": {m: 0.0 for m in MESES_STR},
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


class TestCorteCaixa:
    def test_ano_aberto_novembro(self):
        assert corte_caixa(2026, HOJE) == 10

    def test_ano_fechado(self):
        assert corte_caixa(2025, HOJE) == 12

    def test_ano_futuro(self):
        assert corte_caixa(2027, HOJE) == 0

    def test_janeiro_ainda_sem_ytd(self):
        assert corte_caixa(2026, date(2026, 1, 15)) == 0


class TestFluxoYtdYtg:
    def test_mix_novembro_2026(self):
        real = {m: 0.0 for m in MESES_STR}
        orc = {m: 0.0 for m in MESES_STR}
        real["jan"] = 10.0
        orc["nov"] = 3.0
        orc["dez"] = 2.0
        fluxo = fluxo_ytd_ytg(real, orc, 10)
        assert fluxo["ytd"] == 10.0
        assert fluxo["ytg"] == 5.0
        assert fluxo["geracao"] == 15.0

    def test_corte_zero_e_tudo_ytg(self):
        real = {m: 1.0 for m in MESES_STR}
        orc = {m: 2.0 for m in MESES_STR}
        fluxo = fluxo_ytd_ytg(real, orc, 0)
        assert fluxo["ytd"] == 0.0
        assert fluxo["ytg"] == 24.0

    def test_corte_doze_e_tudo_ytd(self):
        real = {m: 1.0 for m in MESES_STR}
        orc = {m: 99.0 for m in MESES_STR}
        fluxo = fluxo_ytd_ytg(real, orc, 12)
        assert fluxo["ytd"] == 12.0
        assert fluxo["ytg"] == 0.0


class TestSerieVisao:
    def test_saida_negativa_igual_ao_dfc(self):
        rec = [_item(10, realizado={"jan": 100.0}, orcado={"nov": 40.0})]
        desp = [_item(20, realizado={"jan": 30.0}, orcado={"nov": 10.0})]
        real, orc = serie_liquido_visao(_nodes(), rec, desp)
        assert real["jan"] == 70.0
        assert orc["nov"] == 30.0


class TestCadeia:
    def test_2026_abre_no_snapshot_2025(self):
        ab = abertura_encadeada(2026, {2025: 100.0}, {2026: {"geracao": 13.0}})
        assert ab["abertura"] == 100.0
        assert ab["origem"] == "snapshot"
        fim = posicao_fim_ano(2026, ab, {"geracao": 13.0}, {2025: 100.0})
        assert fim["posicao_fim"] == 113.0
        assert fim["origem"] == "projetada"

    def test_2027_abre_na_posicao_projetada_de_2026(self):
        snaps = {2025: 100.0}
        fluxos = {2026: {"geracao": 13.0}, 2027: {"geracao": 4.0}}
        ab = abertura_encadeada(2027, snaps, fluxos)
        assert ab["abertura"] == 113.0
        assert ab["origem"] == "projetada"
        fim = posicao_fim_ano(2027, ab, fluxos[2027], snaps)
        assert fim["posicao_fim"] == 117.0

    def test_ano_fechado_usa_sienge(self):
        ab = abertura_encadeada(2025, {2024: 80.0, 2025: 95.0}, {})
        fim = posicao_fim_ano(2025, ab, {"geracao": 20.0}, {2024: 80.0, 2025: 95.0})
        assert fim["posicao_fim"] == 95.0
        assert fim["origem"] == "snapshot"

    def test_sem_snapshot_nao_inventa(self):
        ab = abertura_encadeada(2026, {}, {2026: {"geracao": 13.0}})
        assert ab["abertura"] is None
        fim = posicao_fim_ano(2026, ab, {"geracao": 13.0}, {})
        assert fim["posicao_fim"] is None


class TestTiposCaixa:
    def test_so_b_i_c(self):
        rows = [
            {"account_type": "B", "amount": 10.0},
            {"account_type": "I", "amount": 20.0},
            {"account_type": "C", "amount": 1.0},
            {"account_type": "M", "amount": 999.0},
            {"account_type": "Q", "amount": 888.0},
            {"account_type": "E", "amount": 777.0},
        ]
        assert saldo_caixa(rows, TIPOS_CAIXA) == 31.0

    def test_tipo_objeto_sienge(self):
        rows = [{"accountType": {"id": "B", "description": "Bancária"}, "amount": 5.0}]
        assert saldo_caixa(rows) == 5.0

    def test_mutuo_pelo_tipo_e_pelo_nome(self):
        assert eh_mutuo(tipo="M", nome="C/C Itaú") is True
        assert eh_mutuo(tipo="C", nome="MUTUO EMPRESA 1") is True
        assert eh_mutuo(tipo="C", nome="Mútuo empresa 14") is True
        assert eh_mutuo(tipo="B", nome="C/C (TERRAS DE ITU) - ITAU") is False
        assert eh_conta_caixa({"account_type": "C", "accountName": "MUTUO EMPRESA 1", "amount": 6800}) is False
        rows = [
            {"account_type": "B", "amount": 10.0, "accountName": "C/C MLDU"},
            {"account_type": "C", "amount": 50.0, "accountName": "MUTUO EMPRESA 1"},
        ]
        assert saldo_caixa(rows) == 10.0


class TestRecorte:
    def test_filtro_empresa_vence(self):
        assert ids_recorte_caixa([{"id_empresa": "4"}], ["32"]) == ["32"]

    def test_sem_filtro_usa_opcoes(self):
        assert ids_recorte_caixa([{"id_empresa": "4"}, {"id_empresa": "32"}], []) == ["32", "4"]


class TestMontarBloco:
    def test_novembro_2026(self):
        rec = [_item(10, realizado={"jan": 100.0}, orcado={"nov": 40.0, "dez": 10.0})]
        desp = [_item(20, realizado={"jan": 20.0}, orcado={"nov": 5.0})]
        rec_n1 = [_item(10, realizado={"jan": 50.0})]
        desp_n1 = [_item(20, realizado={"jan": 10.0})]
        bloco = montar_bloco_geracao(
            ano=2026,
            nodes=_nodes(),
            rec_n=rec,
            desp_n=desp,
            rec_n1=rec_n1,
            desp_n1=desp_n1,
            snapshots={2025: 1000.0, 2024: 900.0},
            hoje=HOJE,
        )
        assert bloco["corte"] == 10
        assert bloco["ytd"] == 80.0
        assert bloco["ytg"] == 45.0
        assert bloco["geracao"] == 125.0
        assert bloco["abertura"] == 1000.0
        assert bloco["posicao_fim"] == 1125.0
        assert bloco["tem_abertura"] is True
        assert bloco["posicao_fim_n1"] == 1000.0
        assert bloco["geracao_n1"] == 40.0
        assert bloco["legenda"] == "abertura 31/12/2025 + YTD + YTG"

    def test_2027_encadeia_2026(self):
        rec_2027 = [_item(10, orcado={"jan": 8.0})]
        desp_2027 = [_item(20, orcado={"jan": 3.0})]
        rec_2026 = [_item(10, realizado={"jan": 100.0}, orcado={"nov": 40.0, "dez": 10.0})]
        desp_2026 = [_item(20, realizado={"jan": 20.0}, orcado={"nov": 5.0})]
        bloco = montar_bloco_geracao(
            ano=2027,
            nodes=_nodes(),
            rec_n=rec_2027,
            desp_n=desp_2027,
            rec_n1=rec_2026,
            desp_n1=desp_2026,
            snapshots={2025: 1000.0},
            hoje=HOJE,
        )
        assert bloco["corte"] == 0
        assert bloco["ytd"] == 0.0
        assert bloco["ytg"] == 5.0
        assert bloco["abertura"] == 1125.0
        assert bloco["posicao_fim"] == 1130.0
        assert bloco["abertura_origem"] == "projetada"
        assert bloco["legenda"] == "abertura projetada 31/12/2026 + YTD + YTG"
