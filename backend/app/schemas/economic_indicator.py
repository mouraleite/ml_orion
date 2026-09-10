from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EconomicIndicatorBase(BaseModel):
    nome: str
    index_type: str
    valor: float
    tipo_unidade: str
    competencia: Optional[str] = None

class EconomicIndicatorCreate(EconomicIndicatorBase):
    pass

class EconomicIndicatorUpdate(BaseModel):
    nome: Optional[str] = None
    index_type: Optional[str] = None
    valor: Optional[float] = None
    tipo_unidade: Optional[str] = None
    competencia: Optional[str] = None

class EconomicIndicator(EconomicIndicatorBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
