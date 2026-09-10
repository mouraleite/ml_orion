import sys; import os; sys.path.append(os.getcwd())
from app.db.database import SessionLocal
from app.api.routes.tracking import _get_tracking_details_logic
import json

db = SessionLocal()

try:
    data = _get_tracking_details_logic(db, "v-258", "consolidado")
    print("Success for v-258!")
    actuals = data.get('kpis', {})
    print("TIR Anual:", actuals.get('tir_anual'))
    print("VGV Total:", actuals.get('vgv_total'))
    print("Exposicao:", actuals.get('exposicao_max_caixa'))
    print("Exposicao VGV:", actuals.get('exposicao_caixa_vgv'))
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    data = _get_tracking_details_logic(db, "cg-11300", "consolidado")
    print("\nSuccess for cg-11300!")
except Exception as e:
    pass
