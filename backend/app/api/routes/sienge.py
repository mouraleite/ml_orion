from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
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
def sync_sienge(current_user=Depends(require_admin)):
    """DESATIVADA em 10/11/2026.

    Sync antigo (Títulos do Contas a Pagar, API REST): buscava os títulos do ano e,
    para cada título, mais 2 chamadas REST (parcelas e apropriação) — uma execução
    esgotaria a cota diária do Sienge. Nenhuma tela chamava; o realizado vem do sync
    diário (POST /sync/sienge e o agendador).
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Rota desativada: use o sync diário (POST /api/v1/sync/sienge).",
    )
