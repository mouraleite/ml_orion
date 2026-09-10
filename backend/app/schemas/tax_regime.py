from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaxRegimeBase(BaseModel):
    nome: str
    pis: Optional[float] = 0.0
    cofins: Optional[float] = 0.0
    irpj: Optional[float] = 0.0
    csll: Optional[float] = 0.0
    outros: Optional[float] = 0.0
    ativo: Optional[bool] = True

class TaxRegimeCreate(TaxRegimeBase):
    pass

class TaxRegimeUpdate(BaseModel):
    nome: Optional[str] = None
    pis: Optional[float] = None
    cofins: Optional[float] = None
    irpj: Optional[float] = None
    csll: Optional[float] = None
    outros: Optional[float] = None
    ativo: Optional[bool] = None

class TaxRegimeResponse(TaxRegimeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
