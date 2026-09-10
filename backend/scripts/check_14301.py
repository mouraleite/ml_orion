import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.cost_center_transaction_data import CostCenterTransactionData

db = SessionLocal()
c = db.query(CostCenter).filter(CostCenter.id_sienge == '14301').first()
if c:
    txs = db.query(CostCenterTransactionData).filter(CostCenterTransactionData.cost_center_id == c.id).all()
    print(f"Transactions for 14301: {len(txs)}")
    total_val = sum(t.total_value for t in txs)
    print(f"Total value: {total_val}")
    
c2 = db.query(CostCenter).filter(CostCenter.id_sienge == '14302').first()
if c2:
    txs2 = db.query(CostCenterTransactionData).filter(CostCenterTransactionData.cost_center_id == c2.id).all()
    print(f"Transactions for 14302: {len(txs2)}")
    total_val2 = sum(t.total_value for t in txs2)
    print(f"Total value 2: {total_val2}")
