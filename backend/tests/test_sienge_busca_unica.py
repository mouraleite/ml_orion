"""Busca única do sync (passo 5, 09/11/2026)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import sienge_busca_unica as bu
from app.services import sienge_sync as ss
from app.services.sienge_client import SiengeFetchError

BASE = "https://x/bulk-data/v1/outcome?startDate=2026-01-01&endDate=2026-01-31"


def test_url_sem_filtro():
    assert bu.url_sem_filtro_de_cc(BASE + "&costCentersId=14100&withX=true") == (BASE + "&withX=true", "14100")
    assert bu.url_sem_filtro_de_cc("https://x/a?costCentersId=7&b=1") == ("https://x/a?b=1", "7")
    assert bu.url_sem_filtro_de_cc("https://x/a?costCentersId=7") == ("https://x/a", "7")
    assert bu.url_sem_filtro_de_cc(BASE) == (BASE, None)


def test_ccs_do_item_em_qualquer_nivel():
    item = {"billId": 1, "paymentsCategories": [{"costCenterId": 14100}],
            "payments": [{"bankMovements": [{"financialCategories": [{"costCenterId": "13900"}]}]}],
            "outro": {"costCenterId": None}}
    assert bu.ccs_do_item(item) == {"14100", "13900"}


ITENS = [
    {"id": 1, "cats": [{"costCenterId": 100}]},
    {"id": 2, "cats": [{"costCenterId": 100}, {"costCenterId": 200}]},
    {"id": 3, "cats": [{"costCenterId": 300}]},
    {"id": 4, "cats": []},
]


def _servidor(chamadas, falhar=False):
    def buscar(url):
        chamadas.append(url)
        yield ITENS[:2]
        if falhar:
            raise SiengeFetchError("caiu na página 2")
        yield ITENS[2:]
    return buscar


def _ids(paginas):
    return sorted(i["id"] for p in paginas for i in p)


def test_cada_cc_recebe_so_os_seus_itens_e_a_busca_e_unica():
    chamadas = []
    with bu.busca_unica(_servidor(chamadas)) as cache:
        assert _ids(cache.paginas_do_cc(BASE + "&costCentersId=100")) == [1, 2]
        assert _ids(cache.paginas_do_cc(BASE + "&costCentersId=200")) == [2]
        assert _ids(cache.paginas_do_cc(BASE + "&costCentersId=300")) == [3]
        assert _ids(cache.paginas_do_cc(BASE + "&costCentersId=999")) == []
    assert chamadas == [BASE]


def test_url_sem_filtro_passa_direto():
    chamadas = []
    with bu.busca_unica(_servidor(chamadas)) as cache:
        assert _ids(cache.paginas_do_cc(BASE)) == [1, 2, 3, 4]
        assert _ids(cache.paginas_do_cc(BASE)) == [1, 2, 3, 4]
    assert chamadas == [BASE, BASE]


def test_falha_no_meio_nao_serve_dados_parciais_e_nao_repete():
    chamadas = []
    with bu.busca_unica(_servidor(chamadas, falhar=True)) as cache:
        with pytest.raises(SiengeFetchError):
            list(cache.paginas_do_cc(BASE + "&costCentersId=100"))
        with pytest.raises(SiengeFetchError):
            list(cache.paginas_do_cc(BASE + "&costCentersId=200"))
    assert chamadas == [BASE]


def test_arquivos_temporarios_sao_apagados():
    with bu.busca_unica(_servidor([])) as cache:
        list(cache.paginas_do_cc(BASE + "&costCentersId=100"))
        pasta = cache._pasta
        assert os.path.isdir(pasta)
    assert not os.path.exists(pasta)
    assert bu.ativa() is None


def test_fetch_do_sync_usa_a_busca_unica_quando_ativa(monkeypatch):
    chamadas = []
    monkeypatch.setattr(ss, "_fetch_paginated_bulk_direto", lambda url: (_ for _ in ()).throw(AssertionError("não devia buscar direto")))
    with bu.busca_unica(_servidor(chamadas)):
        assert _ids(ss._fetch_paginated_bulk(BASE + "&costCentersId=200")) == [2]
    assert chamadas == [BASE]


def test_fora_da_busca_unica_o_fetch_e_o_de_sempre(monkeypatch):
    monkeypatch.setattr(ss, "_fetch_paginated_bulk_direto", lambda url: iter([[{"id": 9}]]))
    assert _ids(ss._fetch_paginated_bulk(BASE + "&costCentersId=200")) == [9]


# --- item 4: todos os centros de custo -------------------------------------------

def test_sync_inclui_todos_os_ccs_com_codigo_sienge(db_session):
    from app.models.cost_center import CostCenter

    db_session.add_all([
        CostCenter(nome="Acompanhado", id_sienge="14100", track_in_dashboard=True),
        CostCenter(nome="Fora do prefixo", id_sienge="72801", track_in_dashboard=False),
        CostCenter(nome="Sem código", id_sienge=None),
    ])
    db_session.flush()
    ids = {c.id_sienge for c in ss.centros_do_sync(db_session)}
    assert {"14100", "72801"} <= ids
    assert None not in ids


def test_vendas_so_para_cc_com_unidades(db_session, monkeypatch):
    from app.models.cost_center import CostCenter
    from app.models.unit import Unit

    vendas = []
    monkeypatch.setattr(ss, "sync_units_se_preciso", lambda db, cc: False)
    monkeypatch.setattr(ss, "sync_sales", lambda db, cc, a, b: vendas.append(cc.id_sienge))
    for nome in ("sync_outcomes", "sync_incomes"):
        monkeypatch.setattr(ss, nome, lambda db, cc, a, b: None)
    for nome in ("mirror_afac_income_as_outcome",):
        monkeypatch.setattr(ss, nome, lambda db, cc, a, b: None)
    for nome in ("sync_receivables_forecast", "sync_payables_forecast", "sync_overdue_open_tracking"):
        monkeypatch.setattr(ss, nome, lambda db, cc, *a, **k: None)

    com = CostCenter(nome="Com lotes", id_sienge="88801")
    sem = CostCenter(nome="Sem lotes", id_sienge="88802")
    db_session.add_all([com, sem])
    db_session.flush()
    db_session.add(Unit(cost_center_id=com.id, id_sienge=1, name="L1"))
    db_session.flush()
    for cc in (com, sem):
        ss.sync_single_cc_sienge_data(db_session, cc, "2026-11-01", "2026-11-09", include_engineering=False)
    assert vendas == ["88801"]
