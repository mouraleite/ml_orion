from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api import deps
from app.models.user import User
from app.models.curves import StandardCurve
from app.schemas.curves import StandardCurveCreate, StandardCurveUpdate, StandardCurveResponse, GenerateDefaultsRequest
import math

router = APIRouter()

@router.get("/", response_model=List[StandardCurveResponse])
def read_curves(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    return db.query(StandardCurve).all()

@router.post("/generate-defaults")
def generate_default_curves(
    *,
    db: Session = Depends(deps.get_db),
    req: GenerateDefaultsRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    months = req.meses
    curve_data = []
    total = 0

    if req.modelo == "s-curve":
        k = 0.3
        x0 = months / 2
        for i in range(1, months + 1):
            val = (math.exp(-k * (i - x0))) / ((1 + math.exp(-k * (i - x0))) ** 2)
            curve_data.append(val)
            total += val
    elif req.modelo == "sino":
        mean = months / 2
        std_dev = months / 4
        for i in range(1, months + 1):
            val = (1 / (std_dev * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((i - mean) / std_dev) ** 2)
            curve_data.append(val)
            total += val
    elif req.modelo == "linear":
        for i in range(1, months + 1):
            curve_data.append(1.0)
            total += 1.0
    else:
        # Default fallback to linear
        for i in range(1, months + 1):
            curve_data.append(1.0)
            total += 1.0

    curve_data = [round((v / total) * 100.0, 2) for v in curve_data]
    
    # Ajuste de arredondamento para cravar em 100%
    diff = 100.0 - sum(curve_data)
    if diff != 0:
        curve_data[-1] = round(curve_data[-1] + diff, 2)
    
    new_curve = StandardCurve(
        nome=f"Curva Padrão ({months} meses) - {req.modelo.capitalize()}",
        tipo=req.tipo,
        valores_meses_json={"meses": curve_data}
    )
    
    db.add(new_curve)
    db.commit()
    return {"message": "Curva padrão gerada com sucesso!"}

@router.post("/", response_model=StandardCurveResponse)
def create_curve(
    *,
    db: Session = Depends(deps.get_db),
    curve_in: StandardCurveCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    curve = StandardCurve(**curve_in.model_dump())
    db.add(curve)
    try:
        db.commit()
        db.refresh(curve)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma curva com este nome. Escolha um nome diferente.")
    return curve

@router.put("/{id}", response_model=StandardCurveResponse)
def update_curve(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    curve_in: StandardCurveUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    curve = db.query(StandardCurve).filter(StandardCurve.id == id).first()
    if not curve:
        raise HTTPException(status_code=404, detail="Curva não encontrada.")
    
    update_data = curve_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(curve, field, value)
        
    try:
        db.commit()
        db.refresh(curve)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma curva com este nome. Escolha um nome diferente.")
    return curve

@router.delete("/{id}")
def delete_curve(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    curve = db.query(StandardCurve).filter(StandardCurve.id == id).first()
    if not curve:
        raise HTTPException(status_code=404, detail="Curva não encontrada.")
    
    # Check if the curve is used in any phase directly
    from app.models.phase import Phase
    from app.models.curves import PhaseCurve
    
    used_in_phase = db.query(Phase).filter(
        (Phase.curva_vendas_id == id) | (Phase.curva_obras_id == id)
    ).first()
    
    used_in_dynamic = db.query(PhaseCurve).filter(
        PhaseCurve.standard_curve_id == id
    ).first()
    
    if used_in_phase or used_in_dynamic:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir esta curva pois ela está sendo utilizada em uma ou mais viabilidades."
        )

    db.delete(curve)
    db.commit()
    return {"ok": True}
