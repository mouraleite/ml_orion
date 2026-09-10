import logging
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.services.erp_integration import ErpIntegrationService
from app.services.sienge_client import SiengeClient
from app.core.config import settings

logger = logging.getLogger(__name__)

def run_daily_sync():
    """
    Task executada pelo Scheduler para rodar diariamente.
    Sincroniza do mês anterior até o fim do ano atual.
    """
    logger.info("Iniciando rotina automática de Sincronização com o Sienge...")
    db = SessionLocal()
    try:
        hoje = datetime.now()
        # Sincroniza desde o início do ano atual até o fim do ano
        start_date = f"{hoje.year}-01-01"
        end_date = f"{hoje.year}-12-31"
        
        subdomain = settings.SIENGE_SUBDOMAIN
        auth_string = SiengeClient.auth_string_from_user_pass(settings.SIENGE_USER, settings.SIENGE_PASS)
        
        service = ErpIntegrationService(db, subdomain, auth_string)
        
        # Sincroniza Despesas
        total = service.sync_realizado_outcome(start_date, end_date, company_id=1)
        logger.info(f"Sincronização diária Sienge finalizada. {total} parcelas de despesas importadas.")
        
    except Exception as e:
        logger.error(f"Erro na Sincronização Sienge Automática: {e}")
    finally:
        db.close()
