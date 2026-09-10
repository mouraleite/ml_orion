import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.deps import require_admin, RoleChecker
from app.models.user import User


def _user(role: str) -> User:
    u = User(id=1, email="t@test.com", full_name="T", role=role, hashed_password="x")
    u.is_active = True
    return u


def test_require_admin_aceita_administrador():
    assert require_admin(user=_user("Administrador")).role == "Administrador"


def test_require_admin_rejeita_gestor():
    with pytest.raises(HTTPException) as exc:
        require_admin(user=_user("Gestor"))
    assert exc.value.status_code == 403


def test_role_checker_gestor_com_alias():
    checker = RoleChecker(["Gestor"])
    assert checker(user=_user("Gestor")).role == "Gestor"
    assert checker(user=_user("Administrador")).role == "Administrador"

    with pytest.raises(HTTPException):
        checker(user=_user("Usuario"))
