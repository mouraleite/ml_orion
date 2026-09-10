from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit
from sqlalchemy import func

def check():
    db = SessionLocal()
    cc_id = 15 # Assuming CC 14100 is id 15, or let's get it dynamically
    from app.models.cost_center import CostCenter
    cc = db.query(CostCenter).filter_by(id_sienge=14100).first()
    if not cc:
        print("CC not found")
        return
        
    fcst_agg = db.query(
        func.substr(ActualTransaction.transaction_date, 1, 7).label("mes"),
        ActualTransaction.category,
        ActualTransaction.transaction_type,
        func.sum(ActualTransaction.value).label("total_value"),
        func.count(ActualTransaction.id).label("count")
    ).filter(
        ActualTransaction.cost_center_id == cc.id,
        ActualTransaction.is_forecast == True
    ).group_by(
        func.substr(ActualTransaction.transaction_date, 1, 7),
        ActualTransaction.category,
        ActualTransaction.transaction_type
    ).all()
    
    print(f"Aggregates for CC {cc.nome} (ID {cc.id}):")
    for row in fcst_agg:
        print(f"Mes: {row.mes}, Cat: {row.category}, Tipo: {row.transaction_type}, Valor: {row.total_value}, Count: {row.count}")
        
    db.close()

if __name__ == "__main__":
    check()
