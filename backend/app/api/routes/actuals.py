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
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    from app.services.erp_integration import erp_service
    
    # Mock parameters
    project_code = f"PROJ-{phase_id}"
    
    mock_data = erp_service.fetch_actuals_for_phase(project_code, phase_id)
    
    inserted = 0
    for item in mock_data:
        existing = db.query(PhaseActuals).filter(
            PhaseActuals.phase_id == phase_id,
            PhaseActuals.categoria == item["categoria"],
            PhaseActuals.mes_referencia == item["mes"]
        ).first()

        if existing:
            existing.valor_realizado = item["valor_realizado"]
            existing.observacao = f"Sincronizado via ERP ({item['origem']})"
        else:
            new_actual = PhaseActuals(
                phase_id=phase_id,
                categoria=item["categoria"],
                mes_referencia=item["mes"],
                valor_realizado=item["valor_realizado"],
                observacao=f"Sincronizado via ERP ({item['origem']})"
            )
            db.add(new_actual)
            inserted += 1

    db.commit()
    
    return {"status": "success", "message": f"Sincronização concluída. {inserted} novos registros, os demais atualizados."}
