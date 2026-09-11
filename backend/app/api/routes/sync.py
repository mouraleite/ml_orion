from fastapi import APIRouter, Depends, BackgroundTasks, Header, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.api import deps
from app.schemas.user import UserResponse
from app.services.sienge_sync import sync_all_sienge_data
from app.core.config import settings
from app.core.scheduler import daily_sienge_sync

router = APIRouter()

@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Retorna o timestamp da última sincronização com as APIs do Sienge."""
    from app.models.system_settings import SystemSettings
    try:
        setting = db.query(SystemSettings).filter_by(key="last_api_sync").first()
        if setting and setting.value:
            ts = setting.value.get("timestamp") if isinstance(setting.value, dict) else str(setting.value)
            return {"last_sync_at": ts}
    except Exception:
        pass
    return {"last_sync_at": None}

@router.post("/sienge")
def trigger_sienge_sync(
    background_tasks: BackgroundTasks,
    full_load: bool = False,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user) # Apenas admin
):
    """
    Dispara o sincronismo manual com as APIs do Sienge (Vendas, Entradas, Saídas).
    """
    # Executa em background para não prender a requisição
    background_tasks.add_task(sync_all_sienge_data, db, full_load)
    
    return {"message": "Sincronismo com Sienge iniciado em background.", "full_load": full_load}


@router.post("/cron")
def trigger_cron_sync(
    background_tasks: BackgroundTasks,
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
):
    """
    Disparo externo (cron-job.org etc.) do sync completo diário.
    Requer header X-Cron-Secret igual a CRON_SECRET no ambiente.
    Acorda a API no plano free e roda o mesmo job do APScheduler.
    """
    expected = (settings.CRON_SECRET or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET não configurado no servidor.",
        )
    if not x_cron_secret or x_cron_secret.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Segredo de cron inválido.",
        )
    background_tasks.add_task(daily_sienge_sync)
    return {
        "message": "Sync diário iniciado em background.",
        "schedule_hint": "09:00 e 14:00 America/Sao_Paulo",
    }
