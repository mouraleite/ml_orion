import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_receivables_forecast, sync_payables_forecast

engine = create_engine("sqlite:///viabilidades.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

cc = db.query(CostCenter).filter(CostCenter.id_sienge.like("141%")).first()
if cc:
    print(f"Syncing CC {cc.nome} ({cc.id_sienge})")
    sync_receivables_forecast(db, cc)
    sync_payables_forecast(db, cc)
else:
    print("CC 141 not found")
