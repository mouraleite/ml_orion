from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ViabilityRevenueBase(BaseModel):
    vgv_total: float = 0.0
    velocidade_vendas_json: Dict[str, Any] = {"meses": []}
    plano_ativo: Optional[str] = None
    condicoes_pagamento_json: List[Dict[str, Any]] = []
    
    sistema_amortizacao: Optional[str] = "Sem Juros"
    taxa_juros_vendas: Optional[float] = 0.0
    indice_correcao_id: Optional[int] = None
    taxa_correcao_projetada: Optional[float] = None
    tipo_correcao_projetada: Optional[str] = "% a.a."
    origem_correcao: Optional[str] = "PROJETADO"
    nome_indice_mercado: Optional[str] = None

class ViabilityRevenueCreate(ViabilityRevenueBase):
    phase_id: int

class ViabilityRevenueUpdate(BaseModel):
    vgv_total: Optional[float] = None
    velocidade_vendas_json: Optional[Dict[str, Any]] = None
    plano_ativo: Optional[str] = None
    condicoes_pagamento_json: Optional[List[Dict[str, Any]]] = None
    
    sistema_amortizacao: Optional[str] = None
    taxa_juros_vendas: Optional[float] = None
    indice_correcao_id: Optional[int] = None
    taxa_correcao_projetada: Optional[float] = None
    tipo_correcao_projetada: Optional[str] = None
    origem_correcao: Optional[str] = None
    nome_indice_mercado: Optional[str] = None

class ViabilityRevenueResponse(ViabilityRevenueBase):
    id: int
    phase_id: int

    model_config = {"from_attributes": True}
