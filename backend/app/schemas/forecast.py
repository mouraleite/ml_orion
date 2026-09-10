from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ForecastItemBase(BaseModel):
    produto_id: int
    plano_financeiro_id: int
    jan: float = 0.0
    fev: float = 0.0
    mar: float = 0.0
    abr: float = 0.0
    mai: float = 0.0
    jun: float = 0.0
    jul: float = 0.0
    ago: float = 0.0
    set: float = 0.0
    out: float = 0.0
    nov: float = 0.0
    dez: float = 0.0
    total_anual: float = 0.0
    observacao: Optional[str] = None

class ForecastDespesasSaveRequest(BaseModel):
    itens: List[ForecastItemBase]

class ForecastVendaMes(BaseModel):
    mes: int
    ticket_medio: float = 0.0
    numero_vendas: int = 0
    vgv: float = 0.0

class ForecastVendaLinha(BaseModel):
    produto_id: int
    plano_venda_id: int
    meses: List[ForecastVendaMes]
    observacao: Optional[str] = None

class ForecastVendasSaveRequest(BaseModel):
    itens: List[ForecastVendaLinha]

class ForecastCreateRequest(BaseModel):
    ano: int
    tipo: str = "DESPESAS"
    versao_base_orcamento_id: Optional[int] = None
    versao_base_forecast_id: Optional[int] = None
    produto_id: Optional[int] = None  # Fase 2: limita o forecast a 1 produto (Centro de Custo)

class ForecastStatusRequest(BaseModel):
    novo_status: str
    motivo: Optional[str] = None
