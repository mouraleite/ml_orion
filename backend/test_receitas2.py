import sys, glob, importlib
sys.path.append('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
for f in glob.glob('app/models/*.py'):
    mod = f.replace('\\', '.').replace('/', '.')[:-3]
    importlib.import_module(mod)
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
db = SessionLocal()
produtos = db.query(CostCenter).filter(CostCenter.status == 'Ativo').all()
planos = db.query(FinancialPlan).filter(FinancialPlan.tp_conta == 'R', FinancialPlan.db_id.like('1%')).all()
print('Produtos:', len(produtos))
print('Planos 1%:', len(planos))

