from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_receivables_forecast, sync_payables_forecast

db = SessionLocal()
cc = db.query(CostCenter).filter(CostCenter.id == 206).first()
if cc:
    print(f"Rodando sync para CC {cc.nome} (Sienge ID: {cc.id_sienge})")
    sync_receivables_forecast(db, cc)
    sync_payables_forecast(db, cc)
else:
    print("CC 206 não encontrado.")
