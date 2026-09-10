from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit
from sqlalchemy import func

def check():
    db = SessionLocal()
    cc_id = 206
    
    fcst_agg = db.query(
        func.substr(ActualTransaction.transaction_date, 1, 7).label("mes"),
        ActualTransaction.category,
        func.sum(ActualTransaction.value).label("total")
    ).filter(
        ActualTransaction.cost_center_id == cc_id,
        ActualTransaction.is_forecast == True,
        ActualTransaction.transaction_type == 'OUTCOME'
    ).group_by(
        func.substr(ActualTransaction.transaction_date, 1, 7),
        ActualTransaction.category
    ).all()
    
    for r in fcst_agg:
        print(f"Mes: {r.mes}, Cat: {r.category}, Total: {r.total}")
        
    db.close()

if __name__ == "__main__":
    check()
