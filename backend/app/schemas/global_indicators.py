from pydantic import BaseModel
from typing import Optional

class GlobalIndicatorsBase(BaseModel):
    ipca_padrao_valor: float = 4.5
    ipca_padrao_tipo: str = "% a.a."
    incc_padrao_valor: float = 5.0
    incc_padrao_tipo: str = "% a.a."

class GlobalIndicatorsCreate(GlobalIndicatorsBase):
    pass

class GlobalIndicatorsUpdate(BaseModel):
    ipca_padrao_valor: Optional[float] = None
    ipca_padrao_tipo: Optional[str] = None
    incc_padrao_valor: Optional[float] = None
    incc_padrao_tipo: Optional[str] = None

class GlobalIndicatorsResponse(GlobalIndicatorsBase):
    id: int

    class Config:
        from_attributes = True
