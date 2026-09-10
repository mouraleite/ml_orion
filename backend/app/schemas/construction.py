from pydantic import BaseModel
from typing import Optional, Dict, Any

class PhaseConstructionBase(BaseModel):
    custo_obras: float = 0.0
    custo_obras_tipo: str = "R$"
    custo_projetos: float = 0.0
    custo_projetos_tipo: str = "%"
    aquisicao_area: float = 0.0
    aquisicao_area_tipo: str = "R$"
    adm_obras: float = 0.0
    adm_obras_tipo: str = "%"
    curva_obras_json: Dict[str, Any] = {"meses": []}
    curva_projetos_json: Dict[str, Any] = {"meses": []}
    curva_aquisicao_json: Dict[str, Any] = {"meses": []}
    curva_adm_obras_json: Dict[str, Any] = {"meses": []}
    extra_constructions_json: list = []

class PhaseConstructionCreate(PhaseConstructionBase):
    phase_id: int

class PhaseConstructionUpdate(BaseModel):
    custo_obras: Optional[float] = None
    custo_obras_tipo: Optional[str] = None
    custo_projetos: Optional[float] = None
    custo_projetos_tipo: Optional[str] = None
    aquisicao_area: Optional[float] = None
    aquisicao_area_tipo: Optional[str] = None
    adm_obras: Optional[float] = None
    adm_obras_tipo: Optional[str] = None
    curva_obras_json: Optional[Dict[str, Any]] = None
    curva_projetos_json: Optional[Dict[str, Any]] = None
    curva_aquisicao_json: Optional[Dict[str, Any]] = None
    curva_adm_obras_json: Optional[Dict[str, Any]] = None
    extra_constructions_json: Optional[list] = None

class PhaseConstructionResponse(PhaseConstructionBase):
    id: int
    phase_id: int

    model_config = {"from_attributes": True}
