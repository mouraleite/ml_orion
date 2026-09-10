from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.api.deps import get_db, require_admin
from app.core.config import settings
from app.services.erp_integration import ErpIntegrationService
from app.services.sienge_client import SiengeClient

router = APIRouter()

def background_sync(db: Session, subdomain: str, auth_string: str, start_date: str, end_date: str):
    service = ErpIntegrationService(db, subdomain, auth_string)
    service.sync_realizado_outcome(start_date, end_date)
    service.sync_realizado_income(start_date, end_date)

@router.post("/sync")
def sync_sienge(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Inicia a sincronização do Sienge no background (somente administrador)."""
    hoje = datetime.now()
    start_date = f"{hoje.year}-01-01"
    end_date = f"{hoje.year}-12-31"

    subdomain = settings.SIENGE_SUBDOMAIN
    auth_string = SiengeClient.auth_string_from_user_pass(settings.SIENGE_USER, settings.SIENGE_PASS)

    background_tasks.add_task(background_sync, db, subdomain, auth_string, start_date, end_date)

    return {"message": "Sincronização iniciada no background."}
