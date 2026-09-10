from pydantic import BaseModel
from typing import Optional

class ScenarioBase(BaseModel):
    nome: str
    vgv_multiplier: Optional[float] = 1.0
    construction_cost_multiplier: Optional[float] = 1.0
    sales_speed_multiplier: Optional[float] = 1.0

class ScenarioCreate(ScenarioBase):
    pass

class ScenarioUpdate(BaseModel):
    nome: Optional[str] = None
    vgv_multiplier: Optional[float] = None
    construction_cost_multiplier: Optional[float] = None
    sales_speed_multiplier: Optional[float] = None

class ScenarioResponse(ScenarioBase):
    id: int

    class Config:
        from_attributes = True
