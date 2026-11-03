import inspect
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.scheduler import daily_sienge_sync
from app.core.sienge_sync_schedule import TZ_BRASILIA, na_janela_do_sync


def test_janela_09h_e_14h():
    assert na_janela_do_sync(datetime(2026, 10, 29, 9, 0, tzinfo=TZ_BRASILIA))
    assert na_janela_do_sync(datetime(2026, 10, 29, 10, 59, tzinfo=TZ_BRASILIA))
    assert na_janela_do_sync(datetime(2026, 10, 29, 14, 0, tzinfo=TZ_BRASILIA))
    assert na_janela_do_sync(datetime(2026, 10, 29, 15, 59, tzinfo=TZ_BRASILIA))


def test_fora_da_janela():
    assert not na_janela_do_sync(datetime(2026, 10, 29, 8, 59, tzinfo=TZ_BRASILIA))
    assert not na_janela_do_sync(datetime(2026, 10, 29, 11, 0, tzinfo=TZ_BRASILIA))
    assert not na_janela_do_sync(datetime(2026, 10, 29, 13, 59, tzinfo=TZ_BRASILIA))
    assert not na_janela_do_sync(datetime(2026, 10, 29, 16, 0, tzinfo=TZ_BRASILIA))


def test_converte_utc_para_brasilia():
    # 12:00 UTC = 09:00 Brasília
    assert na_janela_do_sync(datetime(2026, 10, 29, 12, 0, tzinfo=ZoneInfo("UTC")))


def test_job_das_09h_e_14h_inclui_departamentos():
    src = inspect.getsource(daily_sienge_sync)
    assert "run_sync_departamentos_sienge" in src
    assert "run_sync_empresas" in src
    assert "run_sync_centros_custo" in src
    assert "run_sync_planos_financeiros" in src
    assert "sync_all_sienge_data" in src
    assert "run_integracao_sienge" in src
