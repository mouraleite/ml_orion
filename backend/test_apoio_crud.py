import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import init_db, SessionLocal
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.economic_indicator import EconomicIndicator
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem

def setup_db():
    init_db()
    db = SessionLocal()
    return db

def test_cost_center(db):
    print("Testando Produto (Centro de Custo)...")
    # Tenta ler
    ccs = db.query(CostCenter).all()
    print(f"Total de Produtos (CostCenters): {len(ccs)}")
    
def test_financial_plan(db):
    print("Testando Plano Financeiro...")
    fps = db.query(FinancialPlan).all()
    print(f"Total de Planos Financeiros: {len(fps)}")

def test_payment_plan(db):
    print("Testando Plano de Venda (PaymentPlan)...")
    import uuid
    uid = str(uuid.uuid4())[:8]
    plan = PaymentPlan(nome=f"Plano Teste {uid}", condicoes_json=[{"nome": "A VISTA", "perc": 5.0}])
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Valida restrição de digitação livre no OrcamentoVendaItem
    orc = Orcamento(descricao="Orçamento Teste", ano=2026)
    db.add(orc)
    db.commit()
    db.refresh(orc)
    
    # Criar um item de venda associado ao plano validando a foreign key
    cc = CostCenter(id_sienge=f"PROD_{uid}", nome="Produto Teste")
    db.add(cc)
    db.commit()
    db.refresh(cc)
    
    item = OrcamentoVendaItem(
        orcamento_id=orc.id, 
        produto_id=cc.id, 
        plano_venda_id=plan.id, # <-- APONTAMENTO EXIGIDO!
        mes=1, 
        ano=2026, 
        vgv=1000
    )
    db.add(item)
    db.commit()
    print("Plano de Venda FK OK!")

def test_economic_indicator(db):
    print("Testando Índice de Mercado (EconomicIndicator) com Competência...")
    ind = EconomicIndicator(
        nome="INCC Teste",
        index_type="INCC",
        valor=0.5,
        tipo_unidade="% a.m.",
        competencia="05/2026"
    )
    db.add(ind)
    db.commit()
    db.refresh(ind)
    
    ind_db = db.query(EconomicIndicator).filter(EconomicIndicator.id == ind.id).first()
    assert ind_db.competencia == "05/2026"
    print("Competência no Índice de Mercado OK!")

if __name__ == "__main__":
    db = setup_db()
    try:
        test_cost_center(db)
        test_financial_plan(db)
        test_payment_plan(db)
        test_economic_indicator(db)
        print("TODOS OS TESTES DO MÓDULO DE APOIO PASSARAM!")
    except Exception as e:
        print(f"ERRO: {e}")
    finally:
        # Limpar base de testes (rollback manual se precisar)
        db.rollback()
        # db.close() # Pode fechar aqui
