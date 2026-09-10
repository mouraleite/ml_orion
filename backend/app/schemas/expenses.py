from pydantic import BaseModel
from typing import Optional, Dict, Any

class PhaseExpensesBase(BaseModel):
    marketing_valor: float = 5.0
    marketing_tipo: str = "%"
    comercial_valor: float = 1.0
    comercial_tipo: str = "%"
    comissao_corretagem_valor: float = 0.0
    adm_valor: float = 3.0
    adm_tipo: str = "%"
    curva_marketing_json: Dict[str, Any] = {"meses": []}
    curva_comercial_json: Dict[str, Any] = {"meses": []}
    curva_adm_json: Dict[str, Any] = {"meses": []}
    extra_expenses_json: list = []

class PhaseExpensesCreate(PhaseExpensesBase):
    phase_id: int

class PhaseExpensesUpdate(BaseModel):
    marketing_valor: Optional[float] = None
    marketing_tipo: Optional[str] = None
    comercial_valor: Optional[float] = None
    comercial_tipo: Optional[str] = None
    comissao_corretagem_valor: Optional[float] = None
    adm_valor: Optional[float] = None
    adm_tipo: Optional[str] = None
    curva_marketing_json: Optional[Dict[str, Any]] = None
    curva_comercial_json: Optional[Dict[str, Any]] = None
    curva_adm_json: Optional[Dict[str, Any]] = None
    extra_expenses_json: Optional[list] = None

class PhaseExpensesResponse(PhaseExpensesBase):
    id: int
    phase_id: int

    model_config = {"from_attributes": True}
