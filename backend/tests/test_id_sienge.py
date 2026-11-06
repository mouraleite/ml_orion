"""Sienge ganha do PK interno em centro, obra e obra/centro de custo."""

from types import SimpleNamespace

from app.services.id_sienge import (
    centros_nome_por_id,
    expand_ids_sienge_primeiro,
    resolver_sienge_ou_pk,
)


def _cc(pk, sienge, nome, tipo):
    return SimpleNamespace(id=pk, id_sienge=sienge, nome=nome, tipo=tipo)


CRUZADOS = [
    _cc(70, "14100", "ITU - ALTAVISTA II", "Obra e Centro de Custo"),
    _cc(14100, "70", "FROTA", "Somente Centro de Custo"),
    _cc(4, "17700", "TAGUAI - JARDIM DOS IPÊS III", "Somente Obra"),
    _cc(17700, "4", "CORPORATIVO - TERRAS DE ITU", "Somente Centro de Custo"),
]


def test_centros_nome_por_id_sienge_ganha_em_obra_cc_e_centro():
    mapa = centros_nome_por_id(CRUZADOS)
    assert mapa["14100"] == "ITU - ALTAVISTA II"
    assert mapa["70"] == "FROTA"
    assert mapa["17700"] == "TAGUAI - JARDIM DOS IPÊS III"
    assert mapa["4"] == "CORPORATIVO - TERRAS DE ITU"


def test_resolver_sienge_ou_pk_nao_pega_pk_quando_existe_sienge():
    assert resolver_sienge_ou_pk(CRUZADOS, "70").nome == "FROTA"
    assert resolver_sienge_ou_pk(CRUZADOS, "14100").nome == "ITU - ALTAVISTA II"
    assert resolver_sienge_ou_pk(CRUZADOS, "17700").nome == "TAGUAI - JARDIM DOS IPÊS III"
    assert resolver_sienge_ou_pk(CRUZADOS, "4").nome == "CORPORATIVO - TERRAS DE ITU"


def test_expand_ids_centro_nao_mistura_obra_com_centro():
    assert set(expand_ids_sienge_primeiro(CRUZADOS, ["14100"])) == {"14100"}
    assert set(expand_ids_sienge_primeiro(CRUZADOS, ["70"])) == {"70"}
    assert set(expand_ids_sienge_primeiro(CRUZADOS, ["17700"])) == {"17700"}
    assert set(expand_ids_sienge_primeiro(CRUZADOS, ["4"])) == {"4"}


def test_expand_ids_centro_devolve_so_id_sienge():
    isolado = [_cc(100, "501", "CC Isolado", "Somente Centro de Custo")]
    assert set(expand_ids_sienge_primeiro(isolado, ["501"])) == {"501"}
    assert set(expand_ids_sienge_primeiro(isolado, ["100"])) == {"501"}


def test_mapa_centros_nao_expone_pk_interno():
    isolado = [_cc(100, "501", "CC Isolado", "Somente Centro de Custo")]
    mapa = centros_nome_por_id(isolado)
    assert mapa == {"501": "CC Isolado"}
