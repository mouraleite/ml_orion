import logging
import threading
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.db.database import SessionLocal, engine
from app.api.routes.apoio import run_sync_centros_custo, run_sync_empresas, run_sync_planos_financeiros
from app.core.sienge_sync_schedule import TZ_BRASILIA, na_janela_do_sync
from app.services.depara_autorizacao import run_sync_departamentos_sienge
from app.services.sienge_sync import sync_all_sienge_data
from app.services.integracao_sienge import run_integracao_sienge
from app.core.sync_keepalive import manter_acordado

logger = logging.getLogger(__name__)


_SYNC_LOCK_KEY = 867530901


_LOCAL_SYNC_LOCK = threading.Lock()


def _hold_sync_lock():
    """Trava do sync. Postgres: advisory lock (vale entre processos).
    Outros bancos: trava em memória (vale dentro do processo).
    Retorna False se já houver sync em execução."""
    if engine.dialect.name != "postgresql":
        if not _LOCAL_SYNC_LOCK.acquire(blocking=False):
            return False
        return "local"
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
    if lock_conn is None or lock_conn is False:
        return
    if lock_conn == "local":
        _LOCAL_SYNC_LOCK.release()
        return
    try:
        lock_conn.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": _SYNC_LOCK_KEY},
        )
    finally:
        lock_conn.close()


def run_with_sync_lock(fn, nome: str) -> bool:
    """Roda fn() com a mesma trava do sync diário. False = já havia sync rodando."""
    lock_conn = _hold_sync_lock()
    if lock_conn is False:
        logger.info("%s ignorado: já existe sincronização Sienge em execução.", nome)
        return False
    try:
        fn()
        return True
    finally:
        try:
            _release_sync_lock(lock_conn)
        except Exception:
            logger.exception("Falha ao liberar a trava da sincronização Sienge")


HORAS_SYNC_RECENTE = 2


def ultimo_sync_concluido(db) -> datetime | None:
    """Horário (do servidor) do último sync financeiro concluído sem falhas."""
    from app.models.system_settings import SystemSettings

    try:
        setting = db.query(SystemSettings).filter_by(key="last_api_sync").first()
    except Exception:
        return None
    if not setting or not setting.value:
        return None
    ts = setting.value.get("timestamp") if isinstance(setting.value, dict) else str(setting.value)
    try:
        return datetime.fromisoformat(str(ts))
    except ValueError:
        return None


def sync_concluido_recentemente(db, horas: float = HORAS_SYNC_RECENTE, agora: datetime | None = None) -> bool:
    """True se um sync terminou com sucesso há menos de `horas`.
    O timestamp é gravado com datetime.now() do servidor; comparamos no mesmo relógio."""
    ultimo = ultimo_sync_concluido(db)
    if ultimo is None:
        return False
    agora = agora or datetime.now()
    return timedelta(0) <= agora - ultimo < timedelta(hours=horas)


def daily_sienge_sync(pular_se_recente: bool = True) -> str:
    """Job diário para sincronizar dados do Sienge no banco de dados local.

    Vários gatilhos chamam este job (relógio interno, API acordando na janela,
    GitHub Actions com tentativas repetidas). Por isso:
    - a trava impede dois syncs ao mesmo tempo;
    - se um sync terminou há menos de HORAS_SYNC_RECENTE, a chamada é ignorada;
    - enquanto roda, a API se mantém acordada no Render gratuito.
    Retorna "executado", "em_execucao" ou "recente".
    """
    logger.info("Iniciando sincronização diária (Empresas e Centros de Custo)...")
    lock_conn = _hold_sync_lock()
    if lock_conn is False:
        logger.info("Sincronização Sienge já está em execução. Esta chamada foi ignorada.")
        return "em_execucao"
    try:
        if pular_se_recente:
            db_check = SessionLocal()
            try:
                recente = sync_concluido_recentemente(db_check)
            finally:
                db_check.close()
            if recente:
                logger.info("Sync concluído há menos de %sh. Esta chamada foi ignorada.", HORAS_SYNC_RECENTE)
                return "recente"
        with manter_acordado():
            _executar_sync_diario()
        return "executado"
    finally:
        try:
            _release_sync_lock(lock_conn)
        except Exception:
            logger.exception("Falha ao liberar a trava da sincronização Sienge")


def _executar_sync_diario() -> None:
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

        def _departamentos():
            n = run_sync_departamentos_sienge(db)
            logger.info("Departamentos Sienge (de-para): %s registro(s).", n)

        _etapa("Sincronização de Departamentos Sienge", _departamentos)
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


scheduler = BackgroundScheduler(timezone=TZ_BRASILIA)


def start_scheduler():
    """Inicia o agendador e registra os jobs.
    ERP_ML_DISABLE_SCHEDULER=1 desliga tudo (testes): nada de sync real ao subir a API."""
    import os

    if os.getenv("ERP_ML_DISABLE_SCHEDULER", "").strip() == "1":
        logger.info("APScheduler desligado por ERP_ML_DISABLE_SCHEDULER=1.")
        return
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
