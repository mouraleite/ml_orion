from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.models.user import User

# Mock auth
def override_get_current_active_user():
    return User(id=1, email="test@test.com", is_active=True, role="admin")

app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user

client = TestClient(app)

response = client.get("/api/v1/tracking/summary")
print("STATUS CODE:", response.status_code)
if response.status_code != 200:
    print("ERROR RESPONSE:", response.text)
else:
    print("DATA LENGTH:", len(response.json()))
