import os
import sys

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.deps import get_active_department_id


def _request(headers: dict[str, str], method: str = "GET") -> Request:
    raw = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    return Request({"type": "http", "method": method, "path": "/", "headers": raw, "query_string": b""})


def test_aceita_departamento_ativo():
    assert get_active_department_id(_request({"Departamento-Ativo": "12"})) == 12


def test_x_department_id_tem_prioridade():
    req = _request({"X-Department-Id": "3", "Departamento-Ativo": "99"})
    assert get_active_department_id(req) == 3


def test_falha_sem_header():
    with pytest.raises(HTTPException) as exc:
        get_active_department_id(_request({}))
    assert exc.value.status_code == 400


def test_aceita_sentinela_todos():
    assert get_active_department_id(_request({"X-Department-Id": "0"})) == 0


def test_admin_header_zero_retorna_todos(db_session):
    from app.api.deps import get_active_department
    from app.models.user import User
    from app.services.departamento_leitura import DEPARTAMENTO_TODOS_ID, TODOS_NOME

    user = db_session.query(User).filter(User.id == 1).first()
    dept = get_active_department(_request({"X-Department-Id": "0"}), user, db_session)
    assert dept.id == DEPARTAMENTO_TODOS_ID
    assert dept.nome == TODOS_NOME


def test_usuario_comum_header_zero_403(db_session):
    from app.api.deps import get_active_department
    from app.models.user import User

    user = db_session.query(User).filter(User.id == 2).first()
    with pytest.raises(HTTPException) as exc:
        get_active_department(_request({"X-Department-Id": "0"}), user, db_session)
    assert exc.value.status_code == 403


def test_post_com_todos_rejeita_gravacao(db_session):
    from app.api.deps import get_active_department
    from app.models.user import User

    user = db_session.query(User).filter(User.id == 1).first()
    with pytest.raises(HTTPException) as exc:
        get_active_department(
            _request({"X-Department-Id": "0"}, method="POST"), user, db_session
        )
    assert exc.value.status_code == 400
