from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, List
from app.db.database import get_db
from app.api import deps
from app.models.partnership import PartnershipConfig

router = APIRouter()

@router.get("/")
def get_configs(db: Session = Depends(get_db)):
    return db.query(PartnershipConfig).all()

@router.post("/")
def create_config(data: dict, db: Session = Depends(get_db)):
    if "sienge_prefix" in data:
        existing = db.query(PartnershipConfig).filter(PartnershipConfig.sienge_prefix == data["sienge_prefix"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Já existe uma regra para esta classificação Sienge.")
            
    config = PartnershipConfig(
        name=data.get("name"), 
        sienge_prefix=data.get("sienge_prefix"),
        rules=data.get("rules", {})
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.put("/{id}")
def update_config(id: int, data: dict, db: Session = Depends(get_db)):
    config = db.query(PartnershipConfig).filter(PartnershipConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config não encontrada")
        
    if "sienge_prefix" in data and data["sienge_prefix"] != config.sienge_prefix:
        existing = db.query(PartnershipConfig).filter(PartnershipConfig.sienge_prefix == data["sienge_prefix"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Já existe uma regra para esta classificação Sienge.")
        config.sienge_prefix = data["sienge_prefix"]
        
    if "name" in data:
        config.name = data["name"]
    if "rules" in data:
        config.rules = data["rules"]
    db.commit()
    return config

@router.delete("/{id}")
def delete_config(id: int, db: Session = Depends(get_db)):
    config = db.query(PartnershipConfig).filter(PartnershipConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config não encontrada")
    db.delete(config)
    db.commit()
    return {"ok": True}
