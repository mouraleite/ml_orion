from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction

db = SessionLocal()
try:
    print("Vendas:")
    for r in db.query(ActualTransaction).filter_by(transaction_type="SALE").limit(10).all():
        print(f"{r.source_id}: {r.category} -> {r.value}")
finally:
    db.close()
