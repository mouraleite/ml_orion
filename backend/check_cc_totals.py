from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.actual_transaction import ActualTransaction
from sqlalchemy import func

db = SessionLocal()
cc = db.query(CostCenter).filter_by(id_sienge=70100).first()

if cc:
    outcomes = db.query(func.sum(ActualTransaction.value)).filter_by(
        cost_center_id=cc.id,
        transaction_type='OUTCOME',
        is_forecast=False
    ).scalar() or 0
    
    incomes = db.query(func.sum(ActualTransaction.value)).filter_by(
        cost_center_id=cc.id,
        transaction_type='INCOME',
        is_forecast=False
    ).scalar() or 0
    
    print(f"CC 70100 - Incomes: {incomes:,.2f} | Outcomes: {outcomes:,.2f}")
else:
    print("CC 70100 não encontrado.")
