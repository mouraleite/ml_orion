from sqlalchemy import Column, Integer, Float, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class ViabilityRevenue(Base):
    __tablename__ = "viability_revenues"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    vgv_total = Column(Float, default=0.0) # Will be deprecated/overwritten dynamically
    velocidade_vendas_json = Column(JSON, default=lambda: {"meses": []})
    
    plano_ativo = Column(String, nullable=True) # Nome do plano selecionado
    condicoes_pagamento_json = Column(JSON, default=lambda: []) # Lista de planos e suas condições

    sistema_amortizacao = Column(String, nullable=True, default="Sem Juros")
    taxa_juros_vendas = Column(Float, nullable=True, default=0.0)
    indice_correcao_id = Column(Integer, nullable=True)
    taxa_correcao_projetada = Column(Float, nullable=True)
    tipo_correcao_projetada = Column(String, nullable=True, default="% a.a.")
    origem_correcao = Column(String, nullable=True, default="PROJETADO")
    nome_indice_mercado = Column(String, nullable=True)

    phase = relationship("Phase", back_populates="revenue")
