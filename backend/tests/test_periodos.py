import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.periodos import MESES_STR, skip_linha_total_zero, soma_meses_obj


def test_soma_meses_obj_ignora_none():
    obj = SimpleNamespace(**{m: 0.0 for m in MESES_STR})
    obj.jan = 10
    obj.dez = None
    obj.jun = 2.5
    assert soma_meses_obj(obj) == 12.5


def test_skip_linha_total_zero_preserva_regra_atual():
    vazia = SimpleNamespace(total_anual=0, observacao="")
    com_obs = SimpleNamespace(total_anual=0, observacao="ok")
    com_total = SimpleNamespace(total_anual=1, observacao="")
    assert skip_linha_total_zero(vazia) is True
    assert skip_linha_total_zero(com_obs) is False
    assert skip_linha_total_zero(com_total) is False
