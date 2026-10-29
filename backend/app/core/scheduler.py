import logging
import threading
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.db.database import SessionLocal, engine
from app.api.routes.apoio import run_sync_centros_custo, run_sync_empresas, run_sync_planos_financeiros
from app.core.sienge_sync_schedule import TZ_BRASILIA, na_janela_do_sync
from app.services.sienge_sync import sync_all_sienge_data
from app.services.integracao_sienge import run_integracao_sienge

logger = logging.getLogger(__name__)


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
        def _etapa(nome: str, fn) -> None:
            try:
                fn()
                logger.info("%s concluída.", nome)
            except Exception:
                logger.exception("Falha em %s; seguindo as demais etapas.", nome)
                db.rollback()

        _etapa("Sincronização de Empresas", lambda: run_sync_empresas(db))
        _etapa("Sincronização de Centros de Custo", lambda: run_sync_centros_custo(db))

        def _planos():
            n = run_sync_planos_financeiros(db)
            logger.info("Planos financeiros: %s registro(s) do Sienge.", n)

        _etapa("Sincronização de Planos Financeiros", _planos)
        _etapa(
            "Sincronização Financeira Sienge",
            lambda: sync_all_sienge_data(db, full_load=False),
        )

        def _integracao():
            hoje = datetime.now(TZ_BRASILIA)
            start_date = (hoje - timedelta(days=3)).strftime("%Y-%m-%d")
            end_date = hoje.strftime("%Y-%m-%d")
            run_integracao_sienge(db, start_date, end_date)

        _etapa("Integração Formal", _integracao)
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
            coalesce=True,
            misfire_grace_time=2 * 60 * 60,
        )
        scheduler.start()
    logger.info(
        "APScheduler iniciado. Sync Sienge diário às 09:00 e 14:00 (America/Sao_Paulo)."
    )
    # Plano free dorme: se um ping acordar a API nessa janela, o relógio interno
    # já perdeu o minuto 0. O lock evita corrida com o Cron Job pago.
    if na_janela_do_sync():
        logger.info("API subiu na janela do sync. Disparando job em thread.")
        threading.Thread(
            target=daily_sienge_sync,
            name="sienge-sync-startup",
            daemon=True,
        ).start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler parado.")
