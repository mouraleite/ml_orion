from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User

client = TestClient(app)

def override_get_current_user():
    return User(id=1, email="admin@mouraleite.com.br", role="ADMIN", is_active=True)

app.dependency_overrides[get_current_user] = override_get_current_user

response = client.get("/api/v1/tracking/summary")
print("Status Code:", response.status_code)
if response.status_code == 200:
    print("Items:", len(response.json().get("items", [])))
else:
    print("Error:", response.text)
