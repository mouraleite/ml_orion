import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes.tracking import get_tracking_details, get_tracking_summary
from app.db.database import SessionLocal

db = SessionLocal()
summary = get_tracking_summary(db=db, current_user=None)
for item in summary:
    id = item["id"]
    try:
        det = get_tracking_details(id=id, view_mode="consolidado", db=db, current_user=None)
        cl = det.get("planos_vendas", {}).get("curto_longo", [])
        if any(c.get("value") == 9.0 for c in cl) or any(c.get("value") == 9.1 for c in cl):
            print(f"Found match: {id}")
            print(json.dumps(cl))
            print(json.dumps(det.get("planos_vendas", {}).get("distribuicao", [])))
    except Exception as e:
        pass
