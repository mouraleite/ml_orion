import sys
sys.path.append('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
from app.db.session import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).first()
if phase:
    print("Phase:", phase.id)
    print("Expenses:", phase.expenses.comissao_corretagem_valor if phase.expenses else 'No expenses')
else:
    print("No phase found")
