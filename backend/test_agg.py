import os
import sys

# Configure path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit # Import to avoid KeyError

engine = create_engine("sqlite:///viabilidades.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

fcst_agg = db.query(
    func.substr(ActualTransaction.transaction_date, 1, 7).label("mes"),
    func.sum(ActualTransaction.value).label("total_value"),
).filter(
    ActualTransaction.transaction_type == 'INCOME',
    ActualTransaction.is_forecast == True
).group_by(
    func.substr(ActualTransaction.transaction_date, 1, 7)
).all()

for row in fcst_agg:
    print(row)
