"""De-para: name da autorização Sienge → departamento do Apoio.

Não altera filtro de orçado/realizado — só a sugestão de casamento.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.departamento import Departamento, DeparaAutorizacaoDepartamento
from app.services.depara_autorizacao import (
    run_sync_departamentos_sienge,
    sincronizar_depara,
    sugerir_departamento_id,
)


DEPTS = [
    {"id": 1, "nome": "Engenharia"},
    {"id": 5, "nome": "Engenharia Obras"},
    {"id": 6, "nome": "Tesouraria"},
    {"id": 11, "nome": "Marketing"},
    {"id": 13, "nome": "Gestão de Contratos"},
    {"id": 15, "nome": "Geração de Contratos"},
    {"id": 7, "nome": "Pessoas"},
    {"id": 10, "nome": "Vendas"},
    {"id": 18, "nome": "Consolidado - Sienge"},
]


class TestSugerirDepartamentoId:
    def test_nome_igual(self):
        assert sugerir_departamento_id("Tesouraria", DEPTS) == 6
        assert sugerir_departamento_id("Marketing", DEPTS) == 11
        assert sugerir_departamento_id("Pessoas", DEPTS) == 7
        assert sugerir_departamento_id("Vendas", DEPTS) == 10

    def test_engenharia_obras_nao_cai_em_engenharia(self):
        assert sugerir_departamento_id("Engenharia Obras", DEPTS) == 5
        assert sugerir_departamento_id("Engenharia", DEPTS) == 1

    def test_gestao_nao_vira_geracao(self):
        assert sugerir_departamento_id("Gestão de Contratos", DEPTS) == 13

    def test_sem_cadastro_vai_para_corporativo(self):
        assert sugerir_departamento_id("Departamento Inexistente XYZ", DEPTS) is None
        assert sugerir_departamento_id("", DEPTS) is None

    def test_nao_mapeia_para_consolidado_sienge(self):
        assert sugerir_departamento_id("Consolidado - Sienge", DEPTS) is None

    def test_ignora_acento_e_caixa(self):
        assert sugerir_departamento_id("gestao de contratos", DEPTS) == 13
        assert sugerir_departamento_id("  TESOURARIA  ", DEPTS) == 6


def _seed_depts(db):
    db.add_all(
        [
            Departamento(id=6, nome="Tesouraria"),
            Departamento(id=11, nome="Marketing"),
            Departamento(id=18, nome="Consolidado - Sienge"),
            Departamento(id=5, nome="Engenharia Obras"),
        ]
    )
    db.commit()


class TestSincronizarDepara:
    def test_casa_nome_igual_e_desconhecido_vai_corporativo(self, db_session):
        _seed_depts(db_session)
        rows = sincronizar_depara(
            db_session,
            [
                {"id": 10, "name": "Tesouraria"},
                {"id": 20, "name": "Departamento Inexistente XYZ"},
                {"id": 18, "name": "Consolidado - Sienge"},
            ],
        )
        by_name = {r.nome_sienge: r for r in rows}
        assert by_name["Tesouraria"].departamento_id == 6
        assert by_name["Tesouraria"].definido_manual is False
        assert by_name["Departamento Inexistente XYZ"].departamento_id is None
        assert by_name["Consolidado - Sienge"].departamento_id is None

    def test_manual_nao_e_sobrescrito_no_resync(self, db_session):
        _seed_depts(db_session)
        sincronizar_depara(db_session, [{"id": 10, "name": "Tesouraria"}])
        row = db_session.query(DeparaAutorizacaoDepartamento).filter_by(nome_sienge="Tesouraria").one()
        row.departamento_id = None
        row.definido_manual = True
        db_session.commit()

        sincronizar_depara(db_session, [{"id": 10, "name": "Tesouraria"}])
        row = db_session.query(DeparaAutorizacaoDepartamento).filter_by(nome_sienge="Tesouraria").one()
        assert row.departamento_id is None
        assert row.definido_manual is True

    def test_sugestao_atualiza_quando_nao_e_manual(self, db_session):
        _seed_depts(db_session)
        sincronizar_depara(db_session, [{"id": 99, "name": "Engenharia Obras"}])
        row = db_session.query(DeparaAutorizacaoDepartamento).filter_by(nome_sienge="Engenharia Obras").one()
        assert row.departamento_id == 5
        row.departamento_id = None
        db_session.commit()

        sincronizar_depara(db_session, [{"id": 99, "name": "Engenharia Obras"}])
        row = db_session.query(DeparaAutorizacaoDepartamento).filter_by(nome_sienge="Engenharia Obras").one()
        assert row.departamento_id == 5
        assert row.definido_manual is False

    def test_job_diario_puxa_departments(self, db_session, monkeypatch):
        _seed_depts(db_session)
        monkeypatch.setattr(
            "app.services.sienge_api.get_departamentos",
            lambda: [{"id": 10, "name": "Tesouraria"}],
        )
        n = run_sync_departamentos_sienge(db_session)
        assert n == 1
        row = db_session.query(DeparaAutorizacaoDepartamento).one()
        assert row.nome_sienge == "Tesouraria"
        assert row.departamento_id == 6


class TestDeparaApi:
    def test_list_put_e_sync(self, client, db_session, monkeypatch):
        _seed_depts(db_session)
        monkeypatch.setattr(
            "app.services.sienge_api.get_departamentos",
            lambda: [
                {"id": 10, "name": "Tesouraria"},
                {"id": 77, "name": "Nome Sem Cadastro"},
            ],
        )
        sync = client.post("/api/v1/matriz-permissoes/depara-autorizacao/sync")
        assert sync.status_code == 200
        nomes = {r["nome_sienge"]: r for r in sync.json()}
        assert nomes["Tesouraria"]["departamento_id"] == 6
        assert nomes["Tesouraria"]["departamento_nome"] == "Tesouraria"
        assert nomes["Nome Sem Cadastro"]["departamento_id"] is None
        assert nomes["Nome Sem Cadastro"]["corporativo"] is True

        listed = client.get("/api/v1/matriz-permissoes/depara-autorizacao")
        assert listed.status_code == 200
        assert len(listed.json()) == 2

        row_id = nomes["Nome Sem Cadastro"]["id"]
        put = client.put(
            f"/api/v1/matriz-permissoes/depara-autorizacao/{row_id}",
            json={"departamento_id": 11},
        )
        assert put.status_code == 200
        body = put.json()
        assert body["departamento_id"] == 11
        assert body["departamento_nome"] == "Marketing"
        assert body["definido_manual"] is True
        assert body["corporativo"] is False

        monkeypatch.setattr(
            "app.services.sienge_api.get_departamentos",
            lambda: [{"id": 77, "name": "Nome Sem Cadastro"}],
        )
        again = client.post("/api/v1/matriz-permissoes/depara-autorizacao/sync")
        kept = {r["nome_sienge"]: r for r in again.json()}["Nome Sem Cadastro"]
        assert kept["departamento_id"] == 11
        assert kept["definido_manual"] is True

    def test_put_nao_mapeia_para_consolidado(self, client, db_session, monkeypatch):
        _seed_depts(db_session)
        monkeypatch.setattr(
            "app.services.sienge_api.get_departamentos",
            lambda: [{"id": 10, "name": "Tesouraria"}],
        )
        row_id = client.post("/api/v1/matriz-permissoes/depara-autorizacao/sync").json()[0]["id"]
        bad = client.put(
            f"/api/v1/matriz-permissoes/depara-autorizacao/{row_id}",
            json={"departamento_id": 18},
        )
        assert bad.status_code == 400

    def test_put_corporativo(self, client, db_session, monkeypatch):
        _seed_depts(db_session)
        monkeypatch.setattr(
            "app.services.sienge_api.get_departamentos",
            lambda: [{"id": 10, "name": "Tesouraria"}],
        )
        row_id = client.post("/api/v1/matriz-permissoes/depara-autorizacao/sync").json()[0]["id"]
        put = client.put(
            f"/api/v1/matriz-permissoes/depara-autorizacao/{row_id}",
            json={"departamento_id": None},
        )
        assert put.status_code == 200
        assert put.json()["departamento_id"] is None
        assert put.json()["corporativo"] is True
        assert put.json()["definido_manual"] is True
