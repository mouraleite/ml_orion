"""Otimizações da DFC gerencial mantêm o resultado (11/11/2026)."""
import copy
import math

from app.services.holding_consolidation import _copia
from app.services.orcamento_dfc import MESES_STR
from app.services.orcamento_dfc_gerencial import _mix, _produto_meta


def _orig_mix(key, rec_map, desp_map, serie):
    acc = {m: 0.0 for m in MESES_STR}
    if key in rec_map:
        acc = {m: acc[m] + float(rec_map[key][serie].get(m, 0.0) or 0.0) * 1.0 for m in MESES_STR}
    if key in desp_map:
        acc = {m: acc[m] + float(desp_map[key][serie].get(m, 0.0) or 0.0) * -1.0 for m in MESES_STR}
    return acc


def test_mix_igual_ao_original_inclusive_zero_com_sinal():
    serie = {"jan": -0.0, "fev": 1.5, "mar": None, "abr": 0.0}
    casos = [({"k": {"realizado": serie}}, {}), ({}, {"k": {"realizado": serie}}),
             ({"k": {"realizado": serie}}, {"k": {"realizado": {"jan": 0.0, "fev": 2.0}}}), ({}, {})]
    for rec, desp in casos:
        a, b = _orig_mix("k", rec, desp, "realizado"), _mix("k", rec, desp, "realizado")
        assert a == b
        assert all(math.copysign(1, a[m]) == math.copysign(1, b[m]) for m in MESES_STR)


def test_copia_igual_deepcopy_e_independente():
    item = {"orcado": {"jan": 1.0}, "lista": [{"x": 1}], "nome": "A", "n": None}
    c = _copia(item)
    assert c == copy.deepcopy(item)
    c["orcado"]["jan"] = 9.0
    c["lista"][0]["x"] = 9
    assert item["orcado"]["jan"] == 1.0 and item["lista"][0]["x"] == 1


def test_produto_meta_troca_de_lista():
    a = [{"id": 1, "nome": "CC A", "id_empresa": "E1", "nome_empresa": "Emp 1"}]
    b = [{"id": 1, "nome": "CC B", "id_empresa": "E2", "nome_empresa": "Emp 2"}]
    assert _produto_meta(a, 1)["cc_nome"] == "CC A"
    assert _produto_meta(b, 1)["cc_nome"] == "CC B"
    assert _produto_meta(a, 2)["cc_nome"] == "CC 2"
