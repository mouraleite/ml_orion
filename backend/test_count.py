from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit

db = SessionLocal()
count = db.query(ActualTransaction).filter_by(transaction_type='INCOME', is_forecast=False).count()
print(f'Total INCOME transactions: {count}')
