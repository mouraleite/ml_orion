from pydantic import BaseModel
from typing import Optional

class PhaseBase(BaseModel):
    name: str

class PhaseCreate(PhaseBase):
    viability_id: int

class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    curva_vendas_id: Optional[int] = None
    curva_obras_id: Optional[int] = None

class PhaseResponse(PhaseBase):
    id: int
    viability_id: int
    curva_vendas_id: Optional[int] = None
    curva_obras_id: Optional[int] = None

    model_config = {"from_attributes": True}
