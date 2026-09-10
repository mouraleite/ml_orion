from app.db.database import SessionLocal
from app.api.routes.viabilities import generate_viability_summary, GenerateSummaryRequest

db = SessionLocal()
class MockUser:
    pass

try:
    generate_viability_summary(id=6, request=GenerateSummaryRequest(api_key="foobar"), db=db, current_user=MockUser())
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
