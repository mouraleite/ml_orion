from app.db.database import SessionLocal
from app.services.sienge_sync import sync_all_sienge_data

db = SessionLocal()
try:
    print("Iniciando sincronismo full load (historico completo)...")
    sync_all_sienge_data(db, full_load=True)
    print("Sincronismo concluido!")
finally:
    db.close()
