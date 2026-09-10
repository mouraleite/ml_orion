import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))

from app.api.routes.tracking import get_tracking_details, get_tracking_summary
from app.db.database import SessionLocal

db = SessionLocal()

print("Testing get_tracking_summary...")
summary = get_tracking_summary(db=db, current_user=None)
for item in summary:
    if "slice" in str(item.get("id", "")):
        print(f"Slice Summary: {item['id']} -> TIR: {item['tir_anual']}, Payback: {item['payback_anos']}, ExpMax: {item['exposicao_max_caixa']}")

print("\nTesting get_tracking_details for cg-143_slice_14304...")
try:
    details = get_tracking_details(id="cg-143_slice_14304", view_mode="consolidado", db=db, current_user=None)
    act = details.get("actuals", {})
    print(f"Details: TIR: {act.get('tir_anual')}, Payback: {act.get('payback')}, ExpMax: {act.get('exposicao_maxima')}")
    print(f"Details: VGV Vendido: {act.get('vgv_vendido')}")
    print(f"Details DRE Receita Liquida: {[r for r in details.get('dre', []) if r['item'] == 'RECEITA LÍQUIDA']}")
except Exception as e:
    import traceback
    traceback.print_exc()

