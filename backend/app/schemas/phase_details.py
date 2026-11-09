from pydantic import BaseModel
from typing import Literal, Optional

# ---- TAXES ----
class PhaseTaxesBase(BaseModel):
    regime_tributario: Optional[str] = "RET"
    aliquota_pis: Optional[float] = 0.65
    aliquota_cofins: Optional[float] = 3.0
    aliquota_irpj: Optional[float] = 0.0
    aliquota_csll: Optional[float] = 0.0
    aliquota_outros: Optional[float] = 0.0
    aliquota_total: Optional[float] = 4.0
    incidencia_sobre: Optional[str] = "Recebimento"

class PhaseTaxesCreate(PhaseTaxesBase):
    phase_id: int

class PhaseTaxesUpdate(PhaseTaxesBase):
    pass

class PhaseTaxesResponse(PhaseTaxesBase):
    id: int
    phase_id: int

    class Config:
        from_attributes = True

# ---- EXCHANGES ----
class PhaseExchangesBase(BaseModel):
    modalidade: Optional[str] = "Dinheiro"
    perc_permuta_financeira: Optional[float] = 0.0
    valor_terreno_fixo: Optional[float] = 0.0
    permuta_fisica_unidades: Optional[int] = 0
    permuta_fisica_valor_unidade: Optional[float] = 0.0

    perc_area_terrenista: Optional[float] = 100.0
    perc_area_investidor: Optional[float] = 0.0
    perc_area_empreendedor: Optional[float] = 0.0

    perc_parceria_terrenista: Optional[float] = 38.5
    perc_parceria_investidor: Optional[float] = 0.0
    perc_parceria_empreendedor: Optional[float] = 61.5

    abertura_terrenistas_json: Optional[list] = []
    rateios_config_json: Optional[dict] = {}

class PhaseExchangesCreate(PhaseExchangesBase):
    phase_id: int

class PhaseExchangesUpdate(PhaseExchangesBase):
    pass

class PhaseExchangesResponse(PhaseExchangesBase):
    id: int
    phase_id: int

    class Config:
        from_attributes = True

# ---- FUNDING ----
class PhaseFundingBase(BaseModel):
    percentual_obra_financiado: Optional[float] = 0.0
    taxa_juros: Optional[float] = 0.0
    indexador: Optional[str] = "CDI"
    tipo_funding: Optional[str] = "Plano Empresarial (Banco)"
    modo_volume: Optional[str] = "percentual"
    volume_fixo: Optional[float] = 0.0
    prazo_meses: Optional[int] = 36
    securitizadora: Optional[str] = None
    estrutura_cri: Optional[str] = None
    icvm: Optional[str] = "ICVM 400"
    gross_up: Optional[float] = 9.65
    taxa_estruturacao: Optional[float] = 0.0
    diluir_custos: Optional[bool] = False
    sistema_amortizacao_banco: Optional[str] = "SAC"
    taxa_juros_periodicidade: Optional[Literal["a.a.", "a.m."]] = "a.a."

class PhaseFundingCreate(PhaseFundingBase):
    phase_id: int

class PhaseFundingUpdate(PhaseFundingBase):
    pass

class PhaseFundingResponse(PhaseFundingBase):
    id: int
    phase_id: int

    class Config:
        from_attributes = True

# ---- PHYSICAL DATA ----
class PhasePhysicalDataBase(BaseModel):
    codigo_projeto: Optional[str] = ""
    tipo_projeto: Optional[str] = "Loteamento Fechado"
    cenario: Optional[str] = "Neutro"
    area_total: Optional[float] = 0.0
    area_lotes_residenciais: Optional[float] = 0.0
    area_lotes_comerciais: Optional[float] = 0.0
    area_lotes_mistos: Optional[float] = 0.0
    area_sistema_viario: Optional[float] = 0.0
    area_institucional: Optional[float] = 0.0
    area_verde: Optional[float] = 0.0
    sistema_lazer: Optional[float] = 0.0
    area_associacao: Optional[float] = 0.0
    qtde_lotes_residenciais: Optional[int] = 0
    qtde_lotes_comerciais: Optional[int] = 0
    qtde_lotes_mistos: Optional[int] = 0
    valor_venda_residencial_m2: Optional[float] = 0.0
    valor_venda_comercial_m2: Optional[float] = 0.0
    valor_venda_misto_m2: Optional[float] = 0.0

class PhasePhysicalDataCreate(PhasePhysicalDataBase):
    phase_id: int

class PhasePhysicalDataUpdate(PhasePhysicalDataBase):
    pass

class PhasePhysicalDataResponse(PhasePhysicalDataBase):
    id: int
    phase_id: int

    class Config:
        from_attributes = True

# ---- DATES ----
class PhaseDatesBase(BaseModel):
    data_registro: Optional[str] = None
    data_lancamento: Optional[str] = None
    data_inicio_obras: Optional[str] = None
    data_inicio_projetos: Optional[str] = None
    data_inicio_aquisicao: Optional[str] = None
    data_inicio_comercial: Optional[str] = None
    data_inicio_mkt: Optional[str] = None

class PhaseDatesCreate(PhaseDatesBase):
    phase_id: int

class PhaseDatesUpdate(PhaseDatesBase):
    pass

class PhaseDatesResponse(PhaseDatesBase):
    id: int
    phase_id: int

    class Config:
        from_attributes = True
