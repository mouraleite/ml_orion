import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.sienge_sync import sync_sienge_colaboradores

if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Sincronizando apenas colaboradores...")
        sync_sienge_colaboradores(db)
        print("Finalizado!")
    finally:
        db.close()
