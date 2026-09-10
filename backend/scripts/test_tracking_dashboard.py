import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes.tracking import get_tracking_summary
from app.db.database import SessionLocal

db = SessionLocal()
try:
    print("Testing get_tracking_summary...")
    res = get_tracking_summary(db=db, current_user=None)
    print(f"SUCCESS: {len(res)} items returned.")
    # Try to serialize to JSON to see if it fails
    json_str = json.dumps(res)
    print("JSON Serialization SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    db.close()
