from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    # id_sienge pode ser string pois o frontend espera string para IDs que podem ser "EMP-001" ou numericos
    id_sienge = Column(String, unique=True, index=True)
    cnpj = Column(String, index=True)
    razao_social = Column(String)
    nome_fantasia = Column(String)
    status = Column(String, default="Ativa")
    is_consolidated = Column(Boolean, default=True)
    tipo_empresa = Column(String, default="SPE")

    # Onda B — participação efetiva MLDU (holding)
    participacao_mldu_efetiva = Column(Float, nullable=True)
    participacao_mldu_manual = Column(Float, nullable=True)
    usa_participacao_manual = Column(Boolean, default=False)
    organograma_nota = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamento de Sócios onde esta empresa é a dona/holding de outra (opcional)
    # owned_by = relationship("CompanyPartner", foreign_keys="[CompanyPartner.company_id]", back_populates="company")

class CompanyPartner(Base):
    __tablename__ = "company_partners"

    id = Column(Integer, primary_key=True, index=True)
    
    # A empresa que estamos configurando a sociedade (ex: SPE Obra)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    
    # "Sócio" ou "Parceiro"
    tipo = Column(String, default="Sócio")
    
    # Se o sócio for outra empresa cadastrada no sistema
    partner_company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    
    # Se o sócio/parceiro for externo (ex: João da Silva, ou empresa sem ERP)
    partner_name = Column(String, nullable=True)

    # Sócio pessoa física cadastrado em usuários
    partner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Percentual de participação (ex: 30.5)
    percentage = Column(Float, default=0.0)
    
    # Define se essa participação consolida o balanço
    is_consolidated = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    company = relationship("Company", foreign_keys=[company_id])
    partner_company = relationship("Company", foreign_keys=[partner_company_id])


class CompanyOwnershipLink(Base):
    """Árvore societária MLDU: participação direta pai → filha (Onda B)."""

    __tablename__ = "company_ownership_links"

    id = Column(Integer, primary_key=True, index=True)
    parent_company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    child_company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), unique=True, index=True)
    percentage = Column(Float, nullable=False)
    consolidates = Column(Boolean, default=True)
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent_company = relationship("Company", foreign_keys=[parent_company_id])
    child_company = relationship("Company", foreign_keys=[child_company_id])
    periods = relationship(
        "CompanyOwnershipPeriod",
        back_populates="link",
        cascade="all, delete-orphan",
    )


class CompanyOwnershipPeriod(Base):
    """Faixa de vigência do % direto. Sem linhas = % atual vale para todos os meses."""

    __tablename__ = "company_ownership_periods"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("company_ownership_links.id", ondelete="CASCADE"), index=True, nullable=False)
    percentage = Column(Float, nullable=False)
    valid_from = Column(String, nullable=True)
    valid_until = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    link = relationship("CompanyOwnershipLink", back_populates="periods")
