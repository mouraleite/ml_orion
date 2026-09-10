import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter

engine = create_engine("sqlite:///viabilidades.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Just pick the first CC id that has forecast data
cc = db.query(ActualTransaction.cost_center_id).filter(ActualTransaction.is_forecast == True).first()
if not cc:
    print("No forecast data")
    sys.exit()

cc_id = cc[0]
print(f"Testing for CC: {cc_id}")

fcst_agg = db.query(
    func.substr(ActualTransaction.transaction_date, 1, 7).label("mes"),
    ActualTransaction.category,
    ActualTransaction.transaction_type,
    func.sum(ActualTransaction.value).label("total_value"),
    func.count(ActualTransaction.id).label("count")
).filter(
    ActualTransaction.cost_center_id == cc_id,
    ActualTransaction.is_forecast == True
).group_by(
    func.substr(ActualTransaction.transaction_date, 1, 7),
    ActualTransaction.category,
    ActualTransaction.transaction_type
).all()

for row in fcst_agg:
    print(row)
