import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.api.routes.tracking import get_tracking_details
import json

db = SessionLocal()
res = get_tracking_details("cg-141", "consolidado", db, None)
for row in res.get("dre", []):
    print(row)
