from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.models.tax_regime import TaxRegime
from app.schemas.tax_regime import TaxRegimeCreate, TaxRegimeUpdate, TaxRegimeResponse

router = APIRouter()

@router.get("/", response_model=List[TaxRegimeResponse])
def read_tax_regimes(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tax regimes.
    """
    tax_regimes = db.query(TaxRegime).offset(skip).limit(limit).all()
    return tax_regimes

@router.post("/", response_model=TaxRegimeResponse)
def create_tax_regime(
    *,
    db: Session = Depends(deps.get_db),
    tax_regime_in: TaxRegimeCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new tax regime.
    """
    tax_regime = TaxRegime(**tax_regime_in.model_dump())
    db.add(tax_regime)
    db.commit()
    db.refresh(tax_regime)
    return tax_regime

@router.put("/{id}", response_model=TaxRegimeResponse)
def update_tax_regime(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    tax_regime_in: TaxRegimeUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a tax regime.
    """
    tax_regime = db.query(TaxRegime).filter(TaxRegime.id == id).first()
    if not tax_regime:
        raise HTTPException(status_code=404, detail="Regime Tributário não encontrado")
    
    update_data = tax_regime_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tax_regime, field, value)
        
    db.add(tax_regime)
    db.commit()
    db.refresh(tax_regime)
    return tax_regime

@router.delete("/{id}", response_model=TaxRegimeResponse)
def delete_tax_regime(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a tax regime.
    """
    tax_regime = db.query(TaxRegime).filter(TaxRegime.id == id).first()
    if not tax_regime:
        raise HTTPException(status_code=404, detail="Regime Tributário não encontrado")
    
    db.delete(tax_regime)
    db.commit()
    return tax_regime
