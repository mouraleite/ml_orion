from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base

class RealizadoSienge(Base):
    __tablename__ = "realizado_sienge"

    id = Column(Integer, primary_key=True, index=True)
    id_sienge = Column(String, unique=True, index=True) # Identificador externo
    
    # Referências para conciliação (podem ser nulas se houver pendência de integração INT-SIE-002)
    produto_id_sienge = Column(String, index=True) # Vai ligar com CostCenter.id_sienge
    plano_financeiro_id_sienge = Column(String, index=True) # Vai ligar com FinancialPlan.db_id
    
    mes = Column(Integer)
    ano = Column(Integer)
    valor = Column(Float, default=0.0)
    vgv = Column(Float, default=0.0) # VGV original do Sienge
    tipo = Column(String) # Receita, Despesa, Venda
    
    data_integracao = Column(DateTime, default=datetime.utcnow)

class IntegracaoLog(Base):
    __tablename__ = "integracao_logs"

    id = Column(Integer, primary_key=True, index=True)
    processo = Column(String, index=True) # Ex: "CARGA_REALIZADO_SIENGE", "CARGA_INICIAL_SHAREPOINT"
    inicio = Column(DateTime, default=datetime.utcnow)
    fim = Column(DateTime, nullable=True)
    status = Column(String) # SUCESSO, ERRO, PARCIAL
    volume_processado = Column(Integer, default=0)
    erros = Column(String, nullable=True) # JSON ou Texto com os erros
