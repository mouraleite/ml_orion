from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.snapshot import PhaseSnapshot
from app.schemas.snapshot import PhaseSnapshotCreate, PhaseSnapshotResponse
from app.services.math_engine import calculate_viability_results
import json

router = APIRouter()

@router.post("/phases/{phase_id}/snapshots", response_model=PhaseSnapshotResponse)
def create_phase_snapshot(
    phase_id: int,
    snapshot_in: PhaseSnapshotCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # 1. Roda a matemática
    results = calculate_viability_results(db, phase_id)
    if "error" in results:
        raise HTTPException(status_code=404, detail=results["error"])

    # 2. Verifica a última versão
    last_snapshot = db.query(PhaseSnapshot).filter(PhaseSnapshot.phase_id == phase_id).order_by(PhaseSnapshot.version_number.desc()).first()
    next_version = last_snapshot.version_number + 1 if last_snapshot else 1

    # 3. Se is_baseline == True, remove o baseline dos anteriores
    if snapshot_in.is_baseline:
        db.query(PhaseSnapshot).filter(PhaseSnapshot.phase_id == phase_id).update({"is_baseline": False})

    # 4. Salva o snapshot
    new_snapshot = PhaseSnapshot(
        phase_id=phase_id,
        version_number=next_version,
        is_baseline=snapshot_in.is_baseline,
        snapshot_data=results
    )
    db.add(new_snapshot)
    db.commit()
    db.refresh(new_snapshot)
    return new_snapshot

@router.get("/phases/{phase_id}/snapshots", response_model=List[PhaseSnapshotResponse])
def get_phase_snapshots(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    snapshots = db.query(PhaseSnapshot).filter(PhaseSnapshot.phase_id == phase_id).order_by(PhaseSnapshot.created_at.desc()).all()
    return snapshots

@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(
    snapshot_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    snapshot = db.query(PhaseSnapshot).filter(PhaseSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado.")
    db.delete(snapshot)
    db.commit()
    return {"ok": True}
