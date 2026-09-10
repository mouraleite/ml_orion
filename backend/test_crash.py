from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_incomes

db = SessionLocal()
cc = db.query(CostCenter).filter_by(id_sienge=16111).first()
if cc:
    print(f"Testando sync_incomes para CC {cc.id_sienge}")
    sync_incomes(db, cc, '2026-01-01', '2026-12-31')
else:
    print("CC não encontrado")
