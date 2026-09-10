import os
import sys

# Configure path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# connect directly to the db
engine = create_engine("sqlite:///erp_ml.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- Checking INCOMES ---")
res = db.execute(text("SELECT substr(transaction_date, 1, 4) as ano, transaction_type, sum(value), is_forecast FROM actual_transactions WHERE transaction_type='INCOME' GROUP BY ano, transaction_type, is_forecast ORDER BY ano")).fetchall()
for r in res:
    print(r)

print("--- Checking OUTCOMES ---")
res = db.execute(text("SELECT substr(transaction_date, 1, 4) as ano, transaction_type, sum(value), is_forecast FROM actual_transactions WHERE transaction_type='OUTCOME' GROUP BY ano, transaction_type, is_forecast ORDER BY ano")).fetchall()
for r in res:
    print(r)

