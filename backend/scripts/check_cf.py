import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))

from app.api.routes.tracking import get_tracking_details, _calc_slice_actuals
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter

db = SessionLocal()

print("Checking cash flow for cg-143_slice_14304")
try:
    c = db.query(CostCenter).filter(CostCenter.id_sienge == '14304').first()
    slice_act = _calc_slice_actuals(db, '143', c.id, 0.43502, "consolidado", {})
    
    fc = slice_act.get("fluxo_caixa", [])
    print("Fluxo de Caixa Anual:")
    for row in fc:
        print(f"{row.get('ano')}: Entradas {row.get('Entradas')}, Saidas {row.get('Total_Saidas')}, Saldo {row.get('Saldo_Mes')}")
        
    print("\nTIR Anual:", slice_act.get("tir_anual"))
    print("Exposicao Maxima:", slice_act.get("exposicao_maxima"))

except Exception as e:
    import traceback
    traceback.print_exc()

