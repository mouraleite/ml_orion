"""Realizado de despesas: opções de filtro sem somar o realizado (11/11/2026)."""
from types import SimpleNamespace

from app.services import realizado_sienge as rs


class _Q:
    def __init__(self, linhas):
        self.linhas = linhas
    def with_entities(self, *a):
        return self
    def group_by(self, *a):
        return self
    def order_by(self, *a):
        return self
    def all(self):
        return self.linhas


def test_somente_chaves_cria_as_mesmas_linhas(monkeypatch):
    planos = {"Material": 1, "Retenção": 2}
    monkeypatch.setattr(rs, "build_planos_maps", lambda db: (planos, {1: "N", 2: "S"}))
    linhas_cheias = [(10, "Material", None, 3, 5.0, 5.0), (11, "Retenção", None, 2, -1.0, 1.0), (12, "Outro", None, 1, 9.0, 9.0)]
    combinacoes = [(10, "Material", None, None), (11, "Retenção", None, None), (12, "Outro", None, None)]

    def rodar(somente):
        monkeypatch.setattr(rs, "_consulta_contas_pagar", lambda *a, **k: (_Q(combinacoes), False))
        monkeypatch.setattr(rs, "_linhas_realizado", lambda q, agr, *c: iter(linhas_cheias))
        matriz = {}
        def init_key(p, pl):
            matriz.setdefault((p, pl), {"realizado": {m: 0.0 for m in rs.MESES_STR}})
        rs.agregar_realizado_despesas_sienge(matriz, init_key, None, 2026, [10, 11, 12], [1, 2], somente_chaves=somente)
        return matriz

    cheio, chaves = rodar(False), rodar(True)
    assert list(cheio) == list(chaves) == [(10, 1), (11, 2)]
    assert all(v == 0.0 for k in chaves for v in chaves[k]["realizado"].values())
