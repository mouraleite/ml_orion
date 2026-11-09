from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db, get_current_active_admin, require_admin
from app.models.migration import MigrationMapping
router = APIRouter()

class MigrationMappingResponse(BaseModel):
    id: int
    tipo: str
    nome_origem: str
    id_destino: Optional[int]
    status: str
    data_criacao: datetime

    class Config:
        from_attributes = True

class MigrationMapRequest(BaseModel):
    id: int
    id_destino: int

@router.get("/pendencias", response_model=List[MigrationMappingResponse])
def get_pendencias(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Retorna os itens de De-Para pendentes de mapeamento.
    """
    pendencias = db.query(MigrationMapping).filter(
        MigrationMapping.status == "PENDING"
    ).all()
    return pendencias

@router.post("/map")
def mapear_pendencias(
    req: List[MigrationMapRequest],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Recebe as correções do usuário (De-Para) e atualiza os registros.
    """
    ids = [item.id for item in req]
    mappings = db.query(MigrationMapping).filter(MigrationMapping.id.in_(ids)).all()
    
    mapping_dict = {m.id: m for m in mappings}
    
    for item in req:
        if item.id in mapping_dict:
            mapping = mapping_dict[item.id]
            mapping.id_destino = item.id_destino
            mapping.status = "MAPPED"
            
    db.commit()
    return {"message": "Mapeamentos salvos com sucesso."}

from app.db.database import SessionLocal

def _run_migration_task():
    from app.services.carga_inicial_sharepoint import run_carga_inicial
    db = SessionLocal()
    try:
        run_carga_inicial(db)
    finally:
        db.close()

@router.post("/run")
def run_migration(background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    background_tasks.add_task(_run_migration_task)
    return {"message": "Migração iniciada, cheque o terminal em alguns minutos"}

def _run_forecast_migration_task():
    from app.services.carga_forecast_sharepoint import run_carga_forecast
    db = SessionLocal()
    try:
        run_carga_forecast(db)
    finally:
        db.close()

@router.post("/run-forecast")
def run_forecast_migration(background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    background_tasks.add_task(_run_forecast_migration_task)
    return {"message": "Migração de forecast iniciada, cheque o terminal em alguns minutos"}


@router.post("/run-orcamento-2027")
def run_orcamento_departamentos_2027(
    gravar: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_admin),
):
    """Importa Despesas 2027 de Elaboração do Orçamento (aba fImportacao) por departamento.

    Padrão é simulação (gravar=false). Só grava com gravar=true.
    Só funciona na máquina que tem a pasta do SharePoint sincronizada.
    """
    from app.services.carga_orcamento_departamentos_2027 import (
        importar_orcamentos_departamentos_2027,
    )

    return importar_orcamentos_departamentos_2027(
        db,
        usuario_id=current_user.id,
        gravar=gravar,
    )
