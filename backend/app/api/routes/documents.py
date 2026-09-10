from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.services.sharepoint_service import sp_service
from app.models.phase import Phase

router = APIRouter()

@router.get("/phases/{phase_id}/documents")
def get_documents(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Busca a fase e o projeto para dar nome à pasta
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        return []
    
    project_name = phase.viability.project_name if phase.viability else f"Projeto_{phase_id}"
    docs = sp_service.list_documents(phase_id, project_name)
    return docs

@router.post("/phases/{phase_id}/documents")
async def upload_document(
    phase_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    project_name = phase.viability.project_name if phase and phase.viability else f"Projeto_{phase_id}"
    
    # Mocking file size calculation
    file_size_kb = 120 # Fixo para o mock
    size_str = f"{file_size_kb} KB"

    doc = sp_service.upload_document(phase_id, project_name, file.filename, size_str)
    return {"status": "success", "document": doc}

from pydantic import BaseModel
class DocumentRename(BaseModel):
    new_name: str

@router.put("/phases/{phase_id}/documents/{doc_id}")
def rename_document(
    phase_id: int,
    doc_id: str,
    payload: DocumentRename,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        return {"status": "error", "message": "Phase not found"}
    project_name = phase.viability.project_name if phase.viability else f"Projeto_{phase_id}"
    
    success = sp_service.rename_document(phase_id, project_name, doc_id, payload.new_name)
    if not success:
        return {"status": "error", "message": "Document not found"}
    return {"status": "success"}

@router.delete("/phases/{phase_id}/documents/{doc_id}")
def delete_document(
    phase_id: int,
    doc_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        return {"status": "error", "message": "Phase not found"}
    project_name = phase.viability.project_name if phase.viability else f"Projeto_{phase_id}"
    
    success = sp_service.delete_document(phase_id, project_name, doc_id)
    if not success:
        return {"status": "error", "message": "Document not found"}
    return {"status": "success"}

