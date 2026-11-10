from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.actuals import PhaseActuals
from app.schemas.actuals import PhaseActualsCreate, PhaseActualsResponse

router = APIRouter()

@router.post("/phases/{phase_id}/actuals", response_model=PhaseActualsResponse)
def create_actuals(
    phase_id: int,
    actuals_in: PhaseActualsCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Checar se já existe e atualizar, ou criar um novo. Mas como podem ter múltiplos lançamentos no mesmo mês, vou deixar acumular, ou fazer um "upsert" por mês+categoria.
    # Vamos fazer Upsert para simplificar o dashboard: 1 valor por categoria/mês.
    existing = db.query(PhaseActuals).filter(
        PhaseActuals.phase_id == phase_id,
        PhaseActuals.categoria == actuals_in.categoria,
        PhaseActuals.mes_referencia == actuals_in.mes_referencia
    ).first()

    if existing:
        existing.valor_realizado = actuals_in.valor_realizado
        existing.observacao = actuals_in.observacao
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_actual = PhaseActuals(
            phase_id=phase_id,
            categoria=actuals_in.categoria,
            mes_referencia=actuals_in.mes_referencia,
            valor_realizado=actuals_in.valor_realizado,
            observacao=actuals_in.observacao
        )
        db.add(new_actual)
        db.commit()
        db.refresh(new_actual)
        return new_actual

@router.get("/phases/{phase_id}/actuals", response_model=List[PhaseActualsResponse])
def get_actuals(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    return db.query(PhaseActuals).filter(PhaseActuals.phase_id == phase_id).order_by(PhaseActuals.mes_referencia.asc()).all()

@router.post("/phases/{phase_id}/actuals/sync")
def sync_actuals(
    phase_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """DESATIVADA em 10/11/2026: era um protótipo com dados simulados e chamava uma
    função que não existe mais (fetch_actuals_for_phase). O botão saiu da tela."""
    raise HTTPException(status_code=410, detail="Sincronização desta tela desativada: o realizado vem do sync diário com o Sienge.")
