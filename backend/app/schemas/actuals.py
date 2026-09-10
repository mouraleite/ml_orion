from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PhaseActualsBase(BaseModel):
    categoria: str
    mes_referencia: int
    valor_realizado: float
    observacao: Optional[str] = None

class PhaseActualsCreate(PhaseActualsBase):
    pass

class PhaseActualsResponse(PhaseActualsBase):
    id: int
    phase_id: int
    created_at: datetime

    class Config:
        from_attributes = True
