import sys
import os
import time
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_single_cc_sienge_data

def run_sync():
    db = SessionLocal()
    # Fetch all cost centers that have an id_sienge
    ccs = db.query(CostCenter).filter(CostCenter.id_sienge != None).all()
    
    # Optional: order them by some logic, e.g. length of id_sienge or alphabetically
    ccs = sorted(ccs, key=lambda c: c.id_sienge)
    
    print(f"Iniciando sincronização completa para {len(ccs)} Centros de Custo...")
    
    for idx, c in enumerate(ccs):
        print(f"[{idx+1}/{len(ccs)}] Sincronizando {c.id_sienge} - {c.nome}...")
        try:
            # Pass full date range to ensure everything is pulled
            sync_single_cc_sienge_data(db, c, "2001-01-01", "2050-12-31")
        except Exception as e:
            print(f"Erro ao sincronizar {c.id_sienge}: {str(e)}")
            
        # 5 seconds delay to be extremely safe with the API
        time.sleep(5)
        
    print("Sincronização completa de todos os centros de custo finalizada!")

if __name__ == "__main__":
    run_sync()
