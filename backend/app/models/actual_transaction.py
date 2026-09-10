from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.unit import Unit

class ActualTransaction(Base):
    """
    Guarda transaes financeiras REAIS (Vendas, Recebimentos, Pagamentos)
    que vÍm da integrao com o Sienge para compor a DRE e Fluxo de Caixa real.
    """
    __tablename__ = "actual_transactions"

    id = Column(Integer, primary_key=True, index=True)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id", ondelete="CASCADE"), index=True)
    
    # ID nico que vem da origem (ex: ID da parcela no Sienge ou Contrato) 
    # Serve para evitar duplicaes no sincronismo
    source_id = Column(String, index=True) 
    
    # Tipo da Transao: "SALE" (Venda), "INCOME" (Recebimento/Entrada), "OUTCOME" (Pagamento/Sada)
    transaction_type = Column(String, index=True)
    
    # Categoria mapeada do "De-Para" da Viso (ex: "Obras", "Marketing", "VGV Vendido", "Distrato")
    category = Column(String, index=True)
    
    # Data em que aconteceu (Data do Contrato, ou Data da Baixa/Pagamento)
    transaction_date = Column(Date, index=True)
    
    # Valor total da transao
    value = Column(Float, default=0.0)

    # Vínculo opcional com a Unidade (para Vendas)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)

    # Flag que indica se a transação é uma previsão (parcela em aberto) ou realizada (baixa bancária)
    is_forecast = Column(Boolean, default=False, nullable=False, server_default="0")

    # Quantidade de parcelas do contrato (usado para classificar Plano Curto/Longo em Vendas)
    installments_number = Column(Integer, default=0, nullable=True)

    # Campos Adicionais de Transação (Sienge)
    bill_id = Column(String, index=True, nullable=True)
    creditor_name = Column(String, nullable=True)
    document_name = Column(String, nullable=True)     # documentIdentificationName / Título
    document_number = Column(String, nullable=True)   # documentNumber / Nº Doc
    authorization_name = Column(String, nullable=True, index=True)  # departamentsCosts.name (Sienge)

    # Relacionamento
    cost_center = relationship("CostCenter")
    unit = relationship("Unit", back_populates="transactions")
