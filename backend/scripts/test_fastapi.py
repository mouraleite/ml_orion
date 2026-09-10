import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps

client = TestClient(app)

# Bypass auth for testing
def override_get_current_user():
    return None

app.dependency_overrides[deps.get_current_active_user] = override_get_current_user

try:
    print("Testing /api/v1/tracking/v-2/details with allow_nan=False...")
    response = client.get("/api/v1/tracking/v-2/details")
    print("Status:", response.status_code)
    
    # Try dumping the parsed dict back into string strictly
    json.dumps(response.json(), allow_nan=False)
    print("JSON Serialization Strict SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
