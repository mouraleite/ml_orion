"""Cota REST do Sienge (09/11/2026): unidades só quando preciso; Integração Formal fora do job diário."""
import inspect
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core import scheduler
from app.models.cost_center import CostCenter
from app.models.unit import Unit
from app.services import sienge_sync
from app.services.sienge_sync import UNITS_SYNC_KEY, precisa_sincronizar_unidades, sync_units_se_preciso

HOJE = date(2026, 11, 10)


@pytest.mark.parametrize("ultima,tem_unidades,esperado", [
    (None, True, True),
    (None, False, True),                 # nunca buscou: busca
    ("2026-11-10", True, False),         # já buscou hoje
    ("2026-11-10", False, False),
    ("2026-11-09", True, True),          # com unidades: 1x por dia
    ("2026-11-09", False, False),        # sem unidades: espera 7 dias
    ("2026-11-04", False, False),
    ("2026-11-03", False, True),
    ("lixo", False, True),
])
def test_precisa_sincronizar_unidades(ultima, tem_unidades, esperado):
    assert precisa_sincronizar_unidades(ultima, tem_unidades, HOJE) is esperado


def _cc(db, id_sienge="99901", custom=None):
    cc = CostCenter(nome="CC teste", id_sienge=id_sienge, custom_data=custom or {})
    db.add(cc)
    db.flush()
    return cc


def _id_do_dia(hoje, sufixo=0):
    """id_sienge cuja primeira checagem cai em `hoje` (ver _dia_da_primeira_checagem)."""
    return str(700000 + (hoje.toordinal() % 7) + 7 * sufixo)  # 700000 é múltiplo de 7


def test_busca_e_grava_a_data(db_session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: chamadas.append(cc.id_sienge) or True)
    cc = _cc(db_session, _id_do_dia(HOJE))
    assert sync_units_se_preciso(db_session, cc, hoje=HOJE) is True
    assert chamadas == [cc.id_sienge]
    assert cc.custom_data[UNITS_SYNC_KEY] == "2026-11-10"
    # segunda rodada no mesmo dia: não chama a API
    assert sync_units_se_preciso(db_session, cc, hoje=HOJE) is False
    assert chamadas == [cc.id_sienge]


def test_nao_grava_data_se_a_busca_falhou(db_session, monkeypatch):
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: False)
    cc = _cc(db_session, _id_do_dia(HOJE, 1))
    sync_units_se_preciso(db_session, cc, hoje=HOJE)
    assert UNITS_SYNC_KEY not in (cc.custom_data or {})


def test_cc_com_unidades_busca_todo_dia(db_session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: chamadas.append(1) or True)
    cc = _cc(db_session, "99903", {UNITS_SYNC_KEY: "2026-11-09"})
    db_session.add(Unit(cost_center_id=cc.id, id_sienge=1, name="Lote 1"))
    db_session.flush()
    assert sync_units_se_preciso(db_session, cc, hoje=HOJE) is True
    assert chamadas == [1]


def test_cc_sem_unidades_espera_uma_semana(db_session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: chamadas.append(1) or True)
    cc = _cc(db_session, "99904", {UNITS_SYNC_KEY: "2026-11-09"})
    assert sync_units_se_preciso(db_session, cc, hoje=HOJE) is False
    assert chamadas == []


def test_preserva_o_resto_do_custom_data(db_session, monkeypatch):
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: True)
    cc = _cc(db_session, _id_do_dia(HOJE, 2), {"__cnpj": "123", "land_payment_curve_id": 7})
    sync_units_se_preciso(db_session, cc, hoje=HOJE)
    assert cc.custom_data["__cnpj"] == "123"
    assert cc.custom_data["land_payment_curve_id"] == 7


def test_integracao_formal_fora_do_job_diario():
    src = inspect.getsource(scheduler._executar_sync_diario)
    assert "run_integracao_sienge" not in src
    assert "_etapa(\"Integração Formal\"" not in src


def test_estreia_espalha_ccs_sem_unidades_pela_semana(db_session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: chamadas.append(cc.id_sienge) or True)
    ccs = [_cc(db_session, str(200000 + i)) for i in range(70)]
    sync_por_dia = []
    from datetime import timedelta
    for d in range(7):
        antes = len(chamadas)
        for cc in ccs:
            sync_units_se_preciso(db_session, cc, hoje=HOJE + timedelta(days=d))
        sync_por_dia.append(len(chamadas) - antes)
    assert sync_por_dia == [10] * 7          # 70 CCs, 10 por dia
    assert sorted(chamadas) == sorted(c.id_sienge for c in ccs)  # todos checados na semana


def test_estreia_cc_com_unidades_busca_no_primeiro_dia(db_session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(sienge_sync, "sync_units", lambda db, cc: chamadas.append(1) or True)
    cc = _cc(db_session, _id_do_dia(HOJE, 3) + "1")  # fora do dia dele
    db_session.add(Unit(cost_center_id=cc.id, id_sienge=5, name="Lote"))
    db_session.flush()
    assert sync_units_se_preciso(db_session, cc, hoje=HOJE) is True
