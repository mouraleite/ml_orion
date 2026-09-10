import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import init_db, SessionLocal
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.user import User
from app.models.orcamento import Orcamento, OrcamentoItem
from app.api.routes.orcamentos import get_orcamento_despesas, salvar_orcamento_despesas, OrcamentoSaveRequest, OrcamentoItemCreate
from fastapi import HTTPException

# Mock objects para simular dependências do FastAPI
class MockRequest:
    def __init__(self, headers):
        self.headers = headers

class MockUser:
    def __init__(self, uid):
        self.id = 99999 + uid
        self.role = "Usuario"
        
def setup_db():
    init_db()
    return SessionLocal()

def test_orcamento_despesas(db):
    print("Iniciando testes da Matriz de Orçamento de Despesas (Prompt 6)...")
    
    # 1. Preparar dados
    uid = str(uuid.uuid4())[:8]
    
    dept = Departamento(nome=f"Dept Teste {uid}")
    db.add(dept)
    
    cc_allowed = CostCenter(id_sienge=f"CC_OK_{uid}", nome="Centro Permitido")
    cc_denied = CostCenter(id_sienge=f"CC_NOK_{uid}", nome="Centro Negado")
    db.add(cc_allowed)
    db.add(cc_denied)
    
    fp_allowed = FinancialPlan(name="Plano Permitido", db_id=f"FP_OK_{uid}")
    fp_denied = FinancialPlan(name="Plano Negado", db_id=f"FP_NOK_{uid}")
    db.add(fp_allowed)
    db.add(fp_denied)
    
    user = User(email=f"test{uid}@erp.com", hashed_password="abc")
    db.add(user)
    
    db.commit()
    db.refresh(dept)
    db.refresh(cc_allowed)
    db.refresh(cc_denied)
    db.refresh(fp_allowed)
    db.refresh(fp_denied)
    db.refresh(user)
    
    # Adicionar vínculos permitidos
    db.add(DepartamentoPlano(departamento_id=dept.id, plano_financeiro_id=fp_allowed.id, permitido=True))
    db.add(ProdutoPlanoFinanceiro(produto_id=cc_allowed.id, plano_financeiro_id=fp_allowed.id, permitido=True))
    db.commit()
    
    # 2. Testar GET (Auto-create e filtro de permissões)
    ano_teste = 2030
    resultado_get = get_orcamento_despesas(
        ano=ano_teste,
        db=db,
        dept=dept,
        current_user=user
    )
    
    # Valida Auto-creation
    assert resultado_get["orcamento_id"] is not None
    orc = db.query(Orcamento).filter_by(id=resultado_get["orcamento_id"]).first()
    assert orc.descricao == f"Orçamento {ano_teste}"
    print("[OK] Auto-criação do Orçamento Base OK")
    
    # Valida Filtro
    opcoes_planos = [p["id"] for p in resultado_get["opcoes_planos"]]
    assert fp_allowed.id in opcoes_planos, "Plano permitido não retornou"
    assert fp_denied.id not in opcoes_planos, "Plano negado retornou"
    print("[OK] Filtro de permissões na origem (GET) OK")
    
    # 3. Testar POST (Salvar itens válidos)
    req_data_ok = OrcamentoSaveRequest(
        itens=[
            OrcamentoItemCreate(
                produto_id=cc_allowed.id,
                plano_financeiro_id=fp_allowed.id,
                jan=100.0, fev=200.0, total_anual=300.0
            )
        ]
    )
    salvar_orcamento_despesas(ano=ano_teste, data=req_data_ok, db=db, dept=dept, current_user=user)
    
    itens_salvos = db.query(OrcamentoItem).filter_by(orcamento_id=orc.id).all()
    assert len(itens_salvos) == 1
    assert itens_salvos[0].total_anual == 300.0
    print("[OK] Salvamento de item permitido OK")
    
    # 4. Testar POST (Bloqueio em item não permitido - ORC-DESP-002)
    req_data_nok = OrcamentoSaveRequest(
        itens=[
            OrcamentoItemCreate(
                produto_id=cc_denied.id, # Não tem permissão para usar o plano fp_allowed!
                plano_financeiro_id=fp_allowed.id,
                jan=500.0, total_anual=500.0
            )
        ]
    )
    try:
        salvar_orcamento_despesas(ano=ano_teste, data=req_data_nok, db=db, dept=dept, current_user=user)
        assert False, "Deveria ter bloqueado o item não permitido!"
    except HTTPException as e:
        assert e.status_code == 403
        print("[OK] Bloqueio correto de permissão (HTTP 403) OK")
        
    return uid

def cleanup(db, uid):
    # Limpa apenas os dados de teste deste UID para evitar lixo
    db.query(OrcamentoItem).filter(OrcamentoItem.orcamento.has(Orcamento.descricao == "Orçamento 2030")).delete(synchronize_session=False)
    db.query(Orcamento).filter(Orcamento.descricao == "Orçamento 2030").delete(synchronize_session=False)
    db.query(DepartamentoPlano).filter(DepartamentoPlano.departamento.has(Departamento.nome.like(f"%{uid}%"))).delete(synchronize_session=False)
    db.query(ProdutoPlanoFinanceiro).filter(ProdutoPlanoFinanceiro.produto.has(CostCenter.nome.like(f"%{uid}%"))).delete(synchronize_session=False)
    db.query(Departamento).filter(Departamento.nome.like(f"%{uid}%")).delete(synchronize_session=False)
    db.query(CostCenter).filter(CostCenter.nome.like(f"%{uid}%")).delete(synchronize_session=False)
    db.query(FinancialPlan).filter(FinancialPlan.db_id.like(f"%{uid}%")).delete(synchronize_session=False)
    db.query(User).filter(User.email.like(f"%{uid}%")).delete(synchronize_session=False)
    db.commit()

if __name__ == "__main__":
    db = setup_db()
    uid = None
    try:
        uid = test_orcamento_despesas(db)
        print("TODOS OS TESTES DO ORÇAMENTO DE DESPESAS PASSARAM!")
    except AssertionError as e:
        print(f"FALHA DE ASSERÇÃO: {e}")
    except Exception as e:
        print(f"ERRO GERAL: {e}")
    finally:
        if uid:
            cleanup(db, uid)
        db.close()
