import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.database import SessionLocal
from app.api.routes.apoio import run_sync_empresas, run_sync_centros_custo
from app.services.sienge_sync import sync_all_sienge_data
from app.services.integracao_sienge import run_integracao_sienge

logger = logging.getLogger(__name__)

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


def daily_sienge_sync():
    """Job diário para sincronizar dados do Sienge no banco de dados local."""
    logger.info("Iniciando sincronização diária (Empresas e Centros de Custo)...")
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
    except Exception as e:
        logger.error(f"Erro durante a sincronização diária: {str(e)}")
    finally:
        db.close()


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
