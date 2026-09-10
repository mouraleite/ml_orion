import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.sienge_sync import sync_receivables_forecast, sync_payables_forecast
from app.models.cost_center import CostCenter

db = SessionLocal()
try:
    cc = db.query(CostCenter).filter(CostCenter.id_sienge.like("141%")).first()
    if cc:
        print(f"Syncing CC {cc.nome} ({cc.id_sienge})")
        sync_receivables_forecast(db, cc)
        sync_payables_forecast(db, cc)
    else:
        print("CC 141 not found")
finally:
    db.close()
