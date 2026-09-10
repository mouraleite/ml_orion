import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes.tracking import get_tracking_details
from app.db.database import SessionLocal

db = SessionLocal()
try:
    print("Testing cg-143_slice_14304...")
    res1 = get_tracking_details(id="cg-143_slice_14304", view_mode="consolidado", db=db, current_user=None)
    print("cg-143_slice_14304 SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    print("\nTesting cg-143...")
    res2 = get_tracking_details(id="cg-143", view_mode="consolidado", db=db, current_user=None)
    print("cg-143 SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    print("\nTesting v-2...")
    res3 = get_tracking_details(id="v-2", view_mode="consolidado", db=db, current_user=None)
    print("v-2 SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

finally:
    db.close()
