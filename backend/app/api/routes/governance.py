from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.governance import EconomicIndex
from app.schemas.governance import EconomicIndexCreate, EconomicIndexUpdate, EconomicIndexResponse

router = APIRouter()

@router.get("/indices", response_model=List[EconomicIndexResponse])
def read_indices(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Lista todos os índices macroeconômicos. 
    Qualquer usuário logado pode visualizar.
    """
    indices = db.query(EconomicIndex).all()
    return indices

@router.post("/indices", response_model=EconomicIndexResponse)
def create_index(
    *,
    db: Session = Depends(deps.get_db),
    index_in: EconomicIndexCreate,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Cria um novo índice. Somente ADMIN.
    """
    index = db.query(EconomicIndex).filter(EconomicIndex.name == index_in.name).first()
    if index:
        raise HTTPException(
            status_code=400,
            detail="Já existe um índice com este nome.",
        )
    index = EconomicIndex(**index_in.model_dump())
    db.add(index)
    db.commit()
    db.refresh(index)
    return index

@router.put("/indices/{id}", response_model=EconomicIndexResponse)
def update_index(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    index_in: EconomicIndexUpdate,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Atualiza um índice existente. Somente ADMIN.
    """
    index = db.query(EconomicIndex).filter(EconomicIndex.id == id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Índice não encontrado.")
    
    update_data = index_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(index, field, value)
        
    db.add(index)
    db.commit()
    db.refresh(index)
    return index

@router.delete("/indices/{id}")
def delete_index(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Deleta um índice. Somente ADMIN.
    """
    index = db.query(EconomicIndex).filter(EconomicIndex.id == id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Índice não encontrado.")
    db.delete(index)
    db.commit()
    return {"ok": True}
