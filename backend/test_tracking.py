import sys
import json
from app.db.database import SessionLocal
from app.main import app 
from app.api.routes.tracking import get_tracking_summary

db = SessionLocal()
try:
    print("Testing get_tracking_summary...")
    result = get_tracking_summary(db)
    items = result.get("items", []) if isinstance(result, dict) else result
    print(f"Success! Found {len(items)} items.")
    for it in items:
        print(f"- {it.get('project_name')}: Cat={it.get('category')} Stat={it.get('status')} VGV={it.get('vgv_total')}")
    
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
