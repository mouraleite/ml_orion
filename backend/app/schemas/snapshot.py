from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class PhaseSnapshotCreate(BaseModel):
    is_baseline: bool = False

class PhaseSnapshotResponse(BaseModel):
    id: int
    phase_id: int
    version_number: int
    is_baseline: bool
    created_at: datetime
    snapshot_data: Dict[str, Any]

    class Config:
        from_attributes = True
