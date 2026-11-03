from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ViabilityBase(BaseModel):
    project_name: str
    city: Optional[str] = "Não informado"
    status: Optional[str] = "Rascunho"
    tem_multiplas_fases: Optional[bool] = False
    aplicar_ipca_receitas: Optional[bool] = True
    ipca_projetado_valor: Optional[float] = None
    ipca_projetado_tipo: Optional[str] = "% a.a."
    aplicar_ipca_despesas: Optional[bool] = True
    aplicar_incc_obras: Optional[bool] = True
    aplicar_ipca_projetos: Optional[bool] = True
    aplicar_ipca_aquisicao: Optional[bool] = True
    aplicar_ipca_adm: Optional[bool] = True
    incc_projetado_valor: Optional[float] = None
    incc_projetado_tipo: Optional[str] = "% a.a."
    taxa_desconto_vpl: Optional[float] = 12.0
    parecer_executivo: Optional[str] = None
    parecer_original_ia: Optional[str] = None
    obra_cost_center_id: Optional[int] = None

class ViabilityCreate(ViabilityBase):
    pass

class ViabilityUpdate(BaseModel):
    project_name: Optional[str] = None
    city: Optional[str] = None
    status: Optional[str] = None
    obra_cost_center_id: Optional[int] = None
    tem_multiplas_fases: Optional[bool] = None
    aplicar_ipca_receitas: Optional[bool] = None
    ipca_projetado_valor: Optional[float] = None
    ipca_projetado_tipo: Optional[str] = None
    aplicar_ipca_despesas: Optional[bool] = None
    aplicar_incc_obras: Optional[bool] = None
    aplicar_ipca_projetos: Optional[bool] = None
    aplicar_ipca_aquisicao: Optional[bool] = None
    aplicar_ipca_adm: Optional[bool] = None
    incc_projetado_valor: Optional[float] = None
    incc_projetado_tipo: Optional[str] = None
    taxa_desconto_vpl: Optional[float] = None
    parecer_executivo: Optional[str] = None
    parecer_original_ia: Optional[str] = None

class ViabilityResponse(ViabilityBase):
    id: int
    created_at: datetime
    updated_at: datetime
    version_of_id: Optional[int] = None
    versions: Optional[list['ViabilityResponse']] = []

    model_config = {"from_attributes": True}
