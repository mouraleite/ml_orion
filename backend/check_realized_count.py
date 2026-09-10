from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction

def check():
    db = SessionLocal()
    c = db.query(ActualTransaction).filter_by(cost_center_id=206, is_forecast=False).count()
    print(f"Total realized transactions for CC 206: {c}")
    db.close()

if __name__ == "__main__":
    check()
