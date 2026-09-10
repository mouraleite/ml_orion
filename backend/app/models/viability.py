from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Viability(Base):
    __tablename__ = "viabilities"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True, nullable=False)
    city = Column(String, default="Não informado")
    status = Column(String, default="Em Andamento", nullable=False)
    
    # Parâmetros Globais do Master Plan
    tem_multiplas_fases = Column(Boolean, default=False)
    aplicar_ipca_receitas = Column(Boolean, default=True)
    ipca_projetado_valor = Column(Float, nullable=True)
    ipca_projetado_tipo = Column(String, default="% a.a.")
    
    aplicar_ipca_despesas = Column(Boolean, default=True)
    
    aplicar_incc_obras = Column(Boolean, default=True)
    aplicar_ipca_projetos = Column(Boolean, default=True)
    aplicar_ipca_aquisicao = Column(Boolean, default=True)
    aplicar_ipca_adm = Column(Boolean, default=True)
    incc_projetado_valor = Column(Float, nullable=True)
    incc_projetado_tipo = Column(String, default="% a.a.")
    
    taxa_desconto_vpl = Column(Float, default=12.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    parecer_executivo = Column(Text, nullable=True)
    parecer_original_ia = Column(Text, nullable=True)

    # Relacionamento 1:N com as Fases
    phases = relationship("Phase", back_populates="viability", cascade="all, delete-orphan")
    
    # Versionamento
    version_of_id = Column(Integer, ForeignKey("viabilities.id", ondelete="SET NULL"), nullable=True)
    original_viability = relationship("Viability", remote_side=[id], backref="versions")
    # Futuramente: cost, taxes, funding...
