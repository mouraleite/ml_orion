import os
import sys

# Ajusta o sys.path para garantir que os módulos do app possam ser importados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.sienge_sync import sync_all_sienge_data

def resync():
    print("Iniciando resync historico completo do Sienge...")
    db = SessionLocal()
    try:
        sync_all_sienge_data(db, full_load=True)
        print("Resync finalizado com sucesso!")
    except Exception as e:
        print(f"Erro no resync: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    resync()
