import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.roles import is_admin, is_analista, is_diretor, is_gestor


def test_aliases_administrador_e_gestor():
    assert is_admin("Administrador")
    assert is_admin("ADMIN")
    assert not is_admin("GESTOR")
    assert is_gestor("Gestor")
    assert is_gestor("GESTOR")
    assert is_diretor("DIRETOR")
    assert is_diretor("Administrador")
    assert not is_diretor("Gestor")
    assert is_analista("Analista")
    assert is_analista("Gestor")
    assert not is_analista("Visitante")
    assert not is_analista("Consulta")
