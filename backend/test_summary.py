from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_active_user

client = TestClient(app)
app.dependency_overrides[get_current_active_user] = lambda: {"id": 1}

response = client.get("/api/v1/tracking/summary")
print("STATUS:", response.status_code)
print("JSON:", response.json())
