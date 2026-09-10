import sys
import os
import time
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_single_cc_sienge_data

db = SessionLocal()
ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like('143%')).all()

print(f"Encontrados {len(ccs)} centros de custo para sincronizar sob o prefixo 143.")

for c in ccs:
    print(f"Sincronizando {c.id_sienge} - {c.nome}...")
    try:
        sync_single_cc_sienge_data(db, c, full_load=True) if 'full_load' in sync_single_cc_sienge_data.__code__.co_varnames else sync_single_cc_sienge_data(db, c, "2001-01-01", "2050-12-31")
    except Exception as e:
        print(f"Erro em {c.id_sienge}: {e}")
    # sleep to avoid rate limit
    time.sleep(2)
    
print("Sincronização do prefixo 143 concluída!")
