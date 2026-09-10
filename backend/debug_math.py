import sys
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
try:
    results = calculate_viability_results(db, 2)
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
