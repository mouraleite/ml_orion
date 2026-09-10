from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EconomicIndexBase(BaseModel):
    name: str
    symbol: Optional[str] = "%"
    current_value: float
    projected_value: float

class EconomicIndexCreate(EconomicIndexBase):
    pass

class EconomicIndexUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    current_value: Optional[float] = None
    projected_value: Optional[float] = None

class EconomicIndexResponse(EconomicIndexBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
