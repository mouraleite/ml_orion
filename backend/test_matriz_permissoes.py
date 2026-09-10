import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import init_db, SessionLocal
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.services.auth_matrix import validate_budget_allocation

def setup_db():
    init_db()
    db = SessionLocal()
    return db

def test_matriz(db):
    print("Iniciando testes da Matriz de Permissões (Prompt 5)...")
    uid = str(uuid.uuid4())[:8]
    
    # 1. Criar dados de teste
    # Departamentos
    eng = Departamento(nome=f"Engenharia {uid}")
    mkt_dept = Departamento(nome=f"Marketing {uid}")
    db.add(eng)
    db.add(mkt_dept)
    
    # Produto
    prod_a = CostCenter(id_sienge=f"PROD_A_{uid}", nome="Produto A")
    db.add(prod_a)
    
    # Planos Financeiros
    plano_materiais = FinancialPlan(name="Materiais")
    plano_marketing = FinancialPlan(name="Marketing")
    db.add(plano_materiais)
    db.add(plano_marketing)
    
    db.commit()
    
    # Refresh para obter IDs
    db.refresh(eng)
    db.refresh(mkt_dept)
    db.refresh(prod_a)
    db.refresh(plano_materiais)
    db.refresh(plano_marketing)
    
    # 2. Configurar a Matriz
    # Engenharia -> Materiais (Permitido)
    db.add(DepartamentoPlano(departamento_id=eng.id, plano_financeiro_id=plano_materiais.id, permitido=True))
    
    # Marketing Dept -> Marketing (Permitido)
    db.add(DepartamentoPlano(departamento_id=mkt_dept.id, plano_financeiro_id=plano_marketing.id, permitido=True))
    
    # Produto A -> Materiais (Permitido)
    db.add(ProdutoPlanoFinanceiro(produto_id=prod_a.id, plano_financeiro_id=plano_materiais.id, permitido=True))
    
    # Produto A -> Marketing (Permitido)
    db.add(ProdutoPlanoFinanceiro(produto_id=prod_a.id, plano_financeiro_id=plano_marketing.id, permitido=True))
    
    db.commit()
    
    # 3. Executar Validações
    
    # Caso 1: Engenharia + Produto A + Materiais = Permitido
    res1 = validate_budget_allocation(db, eng.id, prod_a.id, plano_materiais.id)
    assert res1 == True, "Erro no Caso 1: Deveria ser permitido"
    print("[OK] Caso 1: Engenharia + Produto A + Materiais = Permitido")
    
    # Caso 2: Engenharia + Produto A + Marketing = Bloqueado
    # (Engenharia não tem DepartamentoPlano para Marketing)
    res2 = validate_budget_allocation(db, eng.id, prod_a.id, plano_marketing.id)
    assert res2 == False, "Erro no Caso 2: Deveria ser bloqueado"
    print("[OK] Caso 2: Engenharia + Produto A + Marketing = Bloqueado")
    
    # Caso 3: Marketing + Produto A + Marketing = Permitido
    res3 = validate_budget_allocation(db, mkt_dept.id, prod_a.id, plano_marketing.id)
    assert res3 == True, "Erro no Caso 3: Deveria ser permitido"
    print("[OK] Caso 3: Marketing + Produto A + Marketing = Permitido")

if __name__ == "__main__":
    db = setup_db()
    try:
        test_matriz(db)
        print("TODOS OS TESTES DA MATRIZ PASSARAM!")
    except AssertionError as e:
        print(f"FALHA NA ASSERÇÃO: {e}")
    except Exception as e:
        print(f"ERRO GERAL: {e}")
    finally:
        db.close()
