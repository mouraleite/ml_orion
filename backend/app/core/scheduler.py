import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.db.database import SessionLocal, engine
from app.api.routes.apoio import run_sync_empresas, run_sync_centros_custo
from app.services.sienge_sync import sync_all_sienge_data
from app.services.integracao_sienge import run_integracao_sienge

logger = logging.getLogger(__name__)

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


_SYNC_LOCK_KEY = 867530901


def _hold_sync_lock():
    """Trava no Postgres enquanto a conexão ficar aberta. None = banco sem trava."""
    if engine.dialect.name != "postgresql":
        return None
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    locked = conn.execute(
        text("SELECT pg_try_advisory_lock(:key)"),
        {"key": _SYNC_LOCK_KEY},
    ).scalar()
    if not locked:
        conn.close()
        return False
    return conn


def _release_sync_lock(lock_conn) -> None:
    if lock_conn is None:
        return
    try:
        lock_conn.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": _SYNC_LOCK_KEY},
        )
    finally:
        lock_conn.close()


def daily_sienge_sync():
    """Job diário para sincronizar dados do Sienge no banco de dados local."""
    logger.info("Iniciando sincronização diária (Empresas e Centros de Custo)...")
    lock_conn = _hold_sync_lock()
    if lock_conn is False:
        logger.info("Sincronização Sienge já está em execução. Esta chamada foi ignorada.")
        return
    db = SessionLocal()
    try:
        run_sync_empresas(db)
        logger.info("Sincronização de Empresas concluída.")

        run_sync_centros_custo(db)
        logger.info("Sincronização de Centros de Custo concluída.")

        logger.info("Iniciando sincronização Financeira (Bulk Data Sienge)...")
        sync_all_sienge_data(db, full_load=False)
        logger.info("Sincronização Financeira Sienge concluída.")

        logger.info("Iniciando Integração Formal (RealizadoSienge)...")
        hoje = datetime.now(TZ_BRASILIA)
        start_date = (hoje - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = hoje.strftime("%Y-%m-%d")
        run_integracao_sienge(db, start_date, end_date)
        logger.info("Integração Formal concluída.")
    except Exception:
        logger.exception("Erro durante a sincronização diária do Sienge")
        raise
    finally:
        db.close()
        try:
            _release_sync_lock(lock_conn)
        except Exception:
            logger.exception("Falha ao liberar a trava da sincronização Sienge")


scheduler = BackgroundScheduler(timezone=TZ_BRASILIA)


def start_scheduler():
    """Inicia o agendador e registra os jobs."""
    if not scheduler.running:
        # 09:00 e 14:00 no horário de Brasília
        scheduler.add_job(
            daily_sienge_sync,
            trigger=CronTrigger(hour="9,14", minute="0", timezone=TZ_BRASILIA),
            id="daily_sienge_sync_job",
            replace_existing=True,
        )
        scheduler.start()
    logger.info(
        "APScheduler iniciado. Sync Sienge diário às 09:00 e 14:00 (America/Sao_Paulo)."
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler parado.")
