from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class StandardCurveBase(BaseModel):
    nome: str
    tipo: str
    classificacao: str = "Custo"
    valores_meses_json: Dict[str, Any]

class StandardCurveCreate(StandardCurveBase):
    pass

class StandardCurveUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    classificacao: Optional[str] = None
    valores_meses_json: Optional[Dict[str, Any]] = None

class StandardCurveResponse(StandardCurveBase):
    id: int

    model_config = {"from_attributes": True}

class GenerateDefaultsRequest(BaseModel):
    tipo: str
    modelo: str
    meses: int

# ---- PhaseCurve (Vínculo dinâmico entre Fase e Curvas) ----

class PhaseCurveItem(BaseModel):
    """Representa um vínculo individual de curva na fase."""
    standard_curve_id: int
    mes_inicio: int = 1

class PhaseCurvesUpdate(BaseModel):
    """Payload para salvar todas as curvas de uma fase de uma vez."""
    curves: List[PhaseCurveItem]

class PhaseCurveResponse(BaseModel):
    id: int
    phase_id: int
    standard_curve_id: int
    mes_inicio: int

    model_config = {"from_attributes": True}

