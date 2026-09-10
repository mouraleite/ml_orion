"""POST /system/version exige administrador (sem override de auth do conftest)."""
from fastapi.testclient import TestClient

from app.main import app


def test_version_sem_auth_401():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        r = c.post("/api/v1/system/version")
    assert r.status_code in (401, 403)
