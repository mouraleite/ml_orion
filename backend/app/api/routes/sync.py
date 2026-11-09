from fastapi import APIRouter, Depends, BackgroundTasks, Header, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import SessionLocal, get_db
from app.api import deps
from app.schemas.user import UserResponse
from app.services.sienge_sync import run_rewrite_pmt_historico_rateio_job, sync_all_sienge_data
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

def _run_sienge_sync_job(full_load: bool, desde: str | None = None) -> None:
    """Abre sessão própria: a do request já fecha antes do background task.
    Usa a mesma trava do sync agendado: dois syncs nunca rodam juntos."""
    from app.core.scheduler import run_with_sync_lock
    from app.core.sync_keepalive import manter_acordado

    def _job():
        db = SessionLocal()
        try:
            with manter_acordado():
                sync_all_sienge_data(db, full_load, desde=desde)
        finally:
            db.close()

    run_with_sync_lock(_job, "Sync manual")


@router.post("/sienge")
def trigger_sienge_sync(
    background_tasks: BackgroundTasks,
    full_load: bool = False,
    desde: str | None = None,
    current_user: UserResponse = Depends(deps.get_current_active_user),
):
    """
    Dispara o sincronismo manual com as APIs do Sienge (Vendas, Entradas, Saídas).
    Incremental (3 dias): qualquer usuário ativo.
    Carga completa ou recarga a partir de uma data (desde=AAAA-MM-DD): só administrador.
    """
    from datetime import date as _date

    from app.core.roles import is_admin_user

    if (full_load or desde) and not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Carga completa ou recarga: apenas administrador.")
    if desde:
        try:
            d = _date.fromisoformat(desde[:10])
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="desde deve ser AAAA-MM-DD.")
        if d > _date.today() or (_date.today() - d).days > 400:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="desde deve estar entre hoje e 400 dias atrás.")
        desde = d.isoformat()
    background_tasks.add_task(_run_sienge_sync_job, full_load, desde)

    return {"message": "Sincronismo com Sienge iniciado em background.", "full_load": full_load, "desde": desde}


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
    from app.core.scheduler import HORAS_SYNC_RECENTE, sync_concluido_recentemente

    db = SessionLocal()
    try:
        recente = sync_concluido_recentemente(db)
    finally:
        db.close()
    if recente:
        return {
            "message": f"Sync já concluído há menos de {HORAS_SYNC_RECENTE}h. Nada a fazer.",
            "iniciado": False,
        }
    background_tasks.add_task(daily_sienge_sync)
    return {
        "message": "Sync diário iniciado em background.",
        "iniciado": True,
        "schedule_hint": "09:00 e 14:00 America/Sao_Paulo",
    }


@router.post("/pmt-historico-rateio")
def trigger_pmt_historico_rateio(
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(deps.get_current_active_user),
):
    """Regrava PMT legado com financialCategoryRate. Só o acompanhamento lê esse source_id."""
    from app.core.roles import is_admin_user

    if not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administrador.")
    from app.core.scheduler import run_with_sync_lock

    background_tasks.add_task(run_with_sync_lock, run_rewrite_pmt_historico_rateio_job, "Regravação PMT legado")
    return {
        "message": "Regravação do PMT legado iniciada em background.",
        "nota": "Não altera OP1 nem orçamento/forecast.",
    }
