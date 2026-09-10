import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes.tracking import get_tracking_summary
from app.db.database import SessionLocal

db = SessionLocal()
summary = get_tracking_summary(db=db, current_user=None)
for item in summary:
    if "slice" in item["id"]:
        print(item["id"])
        print(f"  TIR: {item['tir_anual']}")
        print(f"  Payback: {item['payback_anos']}")
        print(f"  ExpMax: {item['exposicao_max_caixa']}")
