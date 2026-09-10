import sys
import os

# Adiciona a raiz do backend ao PYTHONPATH para imports locais
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import init_db, SessionLocal, engine
from app.models.user import User
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem

def test_criacao_recuperacao_orcamento():
    print("Inicializando o banco...")
    init_db()
    
    db = SessionLocal()
    try:
        # 1. Preparar dados base
        print("Preparando dados base...")
        # Limpar caso já exista do teste anterior
        db.query(OrcamentoItem).delete()
        db.query(Orcamento).delete()
        db.commit()

        user = db.query(User).filter_by(email="test@orcamento.com").first()
        if not user:
            user = User(full_name="Tester", email="test@orcamento.com", hashed_password="abc")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        cc = db.query(CostCenter).filter_by(id_sienge="999").first()
        if not cc:
            cc = CostCenter(id_sienge="999", nome="Centro Teste")
            db.add(cc)
            db.commit()
            db.refresh(cc)
            
        fp = db.query(FinancialPlan).filter_by(db_id="999").first()
        if not fp:
            fp = FinancialPlan(db_id="999", name="Plano Teste")
            db.add(fp)
            db.commit()
            db.refresh(fp)

        # 2. Criar Orçamento
        print("Criando orçamento...")
        orc = Orcamento(
            descricao="Orçamento 2026 Teste",
            ano=2026,
            usuario_criador_id=user.id
        )
        db.add(orc)
        db.commit()
        db.refresh(orc)
        
        # 3. Adicionar Itens
        print("Adicionando itens...")
        item = OrcamentoItem(
            orcamento_id=orc.id,
            produto_id=cc.id,
            plano_financeiro_id=fp.id,
            jan=100.0,
            fev=200.0,
            total_anual=300.0,
            observacao="Teste de item"
        )
        db.add(item)
        db.commit()

        # 4. Recuperar e Validar
        print("Recuperando orçamento e validando...")
        orc_recuperado = db.query(Orcamento).filter_by(id=orc.id).first()
        
        assert orc_recuperado is not None
        assert orc_recuperado.descricao == "Orçamento 2026 Teste"
        assert len(orc_recuperado.itens_despesa) == 1
        
        item_recuperado = orc_recuperado.itens_despesa[0]
        assert item_recuperado.jan == 100.0
        assert item_recuperado.produto.nome == "Centro Teste"
        assert item_recuperado.plano_financeiro.name == "Plano Teste"
        
        print("SUCESSO: Orçamento e itens criados e recuperados integralmente.")
    
    except Exception as e:
        print("ERRO:", str(e))
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_criacao_recuperacao_orcamento()
