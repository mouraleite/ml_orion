from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.db.database import get_db
from app.api.deps import get_current_active_user, require_admin
from app.models.access_profile import AccessProfile
from pydantic import BaseModel

router = APIRouter()

class AccessProfileBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True
    permissions: Dict[str, Any] = {}

class AccessProfileCreate(AccessProfileBase):
    pass

class AccessProfileResponse(AccessProfileBase):
    id: int
    class Config:
        orm_mode = True

@router.get("/", response_model=List[AccessProfileResponse])
def read_profiles(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return db.query(AccessProfile).all()

@router.post("/", response_model=AccessProfileResponse)
def create_profile(
    profile: AccessProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    db_profile = AccessProfile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.put("/{profile_id}", response_model=AccessProfileResponse)
def update_profile(
    profile_id: int,
    profile: AccessProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    db_profile = db.query(AccessProfile).filter(AccessProfile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    for key, value in profile.dict().items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    db_profile = db.query(AccessProfile).filter(AccessProfile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    from app.models.user import UserPerfil

    linked = db.query(UserPerfil).filter(UserPerfil.perfil_id == profile_id).first()
    if db_profile.users or linked:
        raise HTTPException(status_code=400, detail="Existem usuários vinculados a este perfil.")

    db.delete(db_profile)
    db.commit()
    return {"ok": True}
