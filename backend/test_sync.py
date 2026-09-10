import sys
import os
from app.db.database import SessionLocal
from app.services.sienge_sync import sync_receivables_forecast
from app.models.cost_center import CostCenter

def run():
    db = SessionLocal()
    cc = db.query(CostCenter).filter(CostCenter.id == 206).first()
    if cc:
        print('Iniciando sync receivables forecast para CC 206...')
        sync_receivables_forecast(db, cc)
        print('Fim.')

if __name__ == "__main__":
    run()
