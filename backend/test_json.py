import json
from app.db.database import SessionLocal
from app.api.routes.tracking import get_tracking_summary
from app.main import app

db = SessionLocal()
summary = get_tracking_summary(db)
print("Dumping JSON...")
try:
    json.dumps(summary)
    print("Success! JSON serializable.")
except Exception as e:
    print("Error:", e)
db.close()
