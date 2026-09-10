"""Escopo de departamentos por usuário (Onda A)."""

from types import SimpleNamespace

from app.services.user_department_scope import (
    can_see_all_departments,
    departamentos_for_user,
    first_departamento_nome,
    user_has_department_access,
)


class _Dept:
    def __init__(self, id: int, nome: str, ativo: bool = True):
        self.id = id
        self.nome = nome
        self.ativo = ativo


def test_diretor_ve_todos_departamentos(db_session):
    user = SimpleNamespace(
        full_name="Test",
        role="Diretor",
        perfil=None,
        departamentos=[],
    )
    assert can_see_all_departments(user) is True
    ids = [d.id for d in departamentos_for_user(db_session, user)]
    assert len(ids) >= 1


def test_gestor_somente_vinculos(db_session):
    d1 = _Dept(1, "A")
    d2 = _Dept(2, "B")
    user = SimpleNamespace(
        full_name="Gestor",
        role="Gestor",
        perfil=None,
        departamentos=[d1],
    )
    assert can_see_all_departments(user) is False
    assert user_has_department_access(user, db_session, 1) is True
    assert user_has_department_access(user, db_session, 2) is False
    assert [d.id for d in departamentos_for_user(db_session, user)] == [1]


def test_first_departamento_nome_respeita_ordem(db_session):
    from app.models.departamento import Departamento

    depts = (
        db_session.query(Departamento)
        .filter(Departamento.ativo == True)
        .order_by(Departamento.id)
        .limit(2)
        .all()
    )
    assert first_departamento_nome(db_session, []) is None
    if not depts:
        return
    assert first_departamento_nome(db_session, [depts[0].id]) == depts[0].nome
    if len(depts) > 1:
        assert first_departamento_nome(db_session, [depts[1].id, depts[0].id]) == depts[1].nome
