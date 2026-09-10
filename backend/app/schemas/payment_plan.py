from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PaymentPlanCondition(BaseModel):
    nome: str
    perc: float
    aplica_juros: bool = True
    aplica_correcao: bool = True

class PaymentPlanBase(BaseModel):
    nome: str
    condicoes_json: List[PaymentPlanCondition] = []

class PaymentPlanCreate(PaymentPlanBase):
    pass

class PaymentPlanUpdate(BaseModel):
    nome: Optional[str] = None
    condicoes_json: Optional[List[PaymentPlanCondition]] = None

class PaymentPlanResponse(PaymentPlanBase):
    id: int

    model_config = {"from_attributes": True}
