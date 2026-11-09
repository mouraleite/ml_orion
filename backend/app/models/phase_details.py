from sqlalchemy import Column, Integer, Float, String, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class PhaseTaxes(Base):
    __tablename__ = "phase_taxes"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Generic fields that can be expanded later
    regime_tributario = Column(String, default="RET")
    aliquota_pis = Column(Float, default=0.65)
    aliquota_cofins = Column(Float, default=3.0)
    aliquota_irpj = Column(Float, default=0.0)
    aliquota_csll = Column(Float, default=0.0)
    aliquota_outros = Column(Float, default=0.0)
    aliquota_total = Column(Float, default=4.0)
    incidencia_sobre = Column(String, default="Recebimento") # Venda ou Recebimento

    phase = relationship("Phase", back_populates="taxes")

class PhaseExchanges(Base):
    __tablename__ = "phase_exchanges"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Campos genéricos (já existentes)
    modalidade = Column(String, default="Dinheiro") # Dinheiro, Permuta Física, Permuta Financeira
    perc_permuta_financeira = Column(Float, default=0.0)
    valor_terreno_fixo = Column(Float, default=0.0)
    permuta_fisica_unidades = Column(Integer, default=0)
    permuta_fisica_valor_unidade = Column(Float, default=0.0)
    
    # Composição na Área (%)
    perc_area_terrenista = Column(Float, default=100.0)
    perc_area_investidor = Column(Float, default=0.0)
    perc_area_empreendedor = Column(Float, default=0.0)

    # Composição de Parceria (VGV Ponderada %)
    perc_parceria_terrenista = Column(Float, default=38.5)
    perc_parceria_investidor = Column(Float, default=0.0)
    perc_parceria_empreendedor = Column(Float, default=61.5)

    # Abertura Terrenistas (JSON contendo lista de objetos { nome, percentual })
    abertura_terrenistas_json = Column(JSON, default=lambda: [])

    # Configuração de Rateio por Verba (JSON chave: booleano)
    # Ex: {"custo_obras": false, "marketing": true}
    rateios_config_json = Column(JSON, default=lambda: {})

    phase = relationship("Phase", back_populates="exchanges")

class PhaseFunding(Base):
    __tablename__ = "phase_fundings"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True)
    
    # Generic / Default
    percentual_obra_financiado = Column(Float, default=0.0)
    taxa_juros = Column(Float, default=0.0)
    indexador = Column(String, default="CDI")
    
    # New CRI/CRA Specific Fields
    tipo_funding = Column(String, default="Plano Empresarial (Banco)") # "Plano Empresarial (Banco)", "CRI", "CRA"
    modo_volume = Column(String, default="percentual") # "percentual" or "fixo"
    volume_fixo = Column(Float, default=0.0) # Used if modo_volume == "fixo"
    prazo_meses = Column(Integer, default=36)
    
    # Securitizadora & Estrutura
    securitizadora = Column(String, nullable=True) # e.g. "Vórtx", "Oliveira Trust", "Opea"
    estrutura_cri = Column(String, nullable=True) # e.g. "Guarda-Chuva", "Não Guarda-Chuva"
    icvm = Column(String, default="ICVM 400") # "ICVM 400" or "ICVM 476"
    sistema_amortizacao_banco = Column(String, default="SAC") # "SAC", "Price", "Bullet" (Banco e CRI/CRA)
    taxa_juros_periodicidade = Column(String, default="a.a.") # "a.a." ou "a.m.": como taxa_juros foi digitada
    
    # Fees & Taxes
    gross_up = Column(Float, default=9.65) # PIS/COFINS etc in %
    taxa_estruturacao = Column(Float, default=0.0) # Structuring fee % or flat
    
    # Flow Options
    diluir_custos = Column(Boolean, default=False) # True = Dilute over construction, False = Month 1

    phase = relationship("Phase", back_populates="funding")

class PhasePhysicalData(Base):
    __tablename__ = "phase_physical_data"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Configurações Gerais
    codigo_projeto = Column(String, default="")
    tipo_projeto = Column(String, default="Loteamento Fechado")
    cenario = Column(String, default="Neutro")

    # Projeto Urbanístico (m²)
    area_total = Column(Float, default=0.0)
    area_lotes_residenciais = Column(Float, default=0.0)
    area_lotes_comerciais = Column(Float, default=0.0)
    area_lotes_mistos = Column(Float, default=0.0)
    area_sistema_viario = Column(Float, default=0.0)
    area_institucional = Column(Float, default=0.0)
    area_verde = Column(Float, default=0.0)
    sistema_lazer = Column(Float, default=0.0)
    area_associacao = Column(Float, default=0.0)

    # Dados Físicos (Unidades)
    qtde_lotes_residenciais = Column(Integer, default=0)
    qtde_lotes_comerciais = Column(Integer, default=0)
    qtde_lotes_mistos = Column(Integer, default=0)

    # Dados Financeiros (Premissas Base R$/m²)
    valor_venda_residencial_m2 = Column(Float, default=0.0)
    valor_venda_comercial_m2 = Column(Float, default=0.0)
    valor_venda_misto_m2 = Column(Float, default=0.0)

    phase = relationship("Phase", back_populates="physical_data")

class PhaseDates(Base):
    __tablename__ = "phase_dates"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Dates (Format YYYY-MM-DD or simple String)
    data_registro = Column(String, nullable=True)
    data_lancamento = Column(String, nullable=True)
    data_inicio_obras = Column(String, nullable=True)
    data_inicio_projetos = Column(String, nullable=True)
    data_inicio_aquisicao = Column(String, nullable=True)
    data_inicio_comercial = Column(String, nullable=True)
    data_inicio_mkt = Column(String, nullable=True)

    phase = relationship("Phase", back_populates="dates")
