import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.api.routes.tracking import _calc_actuals_for_cc
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter

db = SessionLocal()

print("Checking native actuals for 14304")
try:
    c = db.query(CostCenter).filter(CostCenter.id_sienge == '14304').first()
    act = _calc_actuals_for_cc(db, c.id, None, 1.0, 1.0, {})
    
    print("Native FC:")
    for row in act.get("fluxo_caixa", []):
        print(row)
        
except Exception as e:
    import traceback
    traceback.print_exc()
