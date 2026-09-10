"""Passo 4: escopo de leitura por departamento (orçado, realizado, catálogo, Todos)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.cost_center import CostCenter
from app.models.departamento import (
    Departamento,
    DepartamentoPlano,
    DeparaAutorizacaoDepartamento,
)
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento
from app.services.departamento_leitura import (
    DEPARTAMENTO_TODOS_ID,
    criterio_departamento,
    departamento_id_realizado,
    departamento_sentinela_todos,
    parcela_pertence_ao_dept,
    planos_ids_leitura,
    produtos_ids_leitura,
)


def _depts_leitura(db):
    tes = Departamento(id=6, nome="Tesouraria")
    mkt = Departamento(id=11, nome="Marketing Leitura")
    corp = Departamento(id=18, nome="Corporativo", is_residual=True)
    db.add_all([tes, mkt, corp])
    db.flush()
    return tes, mkt, corp


class TestDepartamentoIdRealizado:
    def test_nome_tesouraria_casa(self, db_session):
        tes, _, corp = _depts_leitura(db_session)
        db_session.commit()
        assert departamento_id_realizado(db_session, "Tesouraria") == tes.id
        assert departamento_id_realizado(db_session, "Tesouraria") != corp.id

    def test_desconhecido_e_sem_nome_vao_corporativo(self, db_session):
        _, _, corp = _depts_leitura(db_session)
        db_session.commit()
        assert departamento_id_realizado(db_session, "Depto Sienge Sem Cadastro") == corp.id
        assert departamento_id_realizado(db_session, None) == corp.id
        assert departamento_id_realizado(db_session, "") == corp.id

    def test_depara_manual_vence_sugestao_por_nome(self, db_session):
        tes, mkt, _ = _depts_leitura(db_session)
        db_session.add(
            DeparaAutorizacaoDepartamento(
                nome_sienge="Tesouraria",
                departamento_id=mkt.id,
                definido_manual=True,
            )
        )
        db_session.commit()
        assert departamento_id_realizado(db_session, "Tesouraria") == mkt.id
        assert departamento_id_realizado(db_session, "Tesouraria") != tes.id


class TestCriterioOrcamento:
    def test_orcado_de_marketing_nao_aparece_em_tesouraria(self, db_session):
        tes, mkt, _ = _depts_leitura(db_session)
        db_session.add_all(
            [
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=mkt.id, descricao="MKT"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=tes.id, descricao="TES"),
            ]
        )
        db_session.commit()
        ids = {
            o.descricao
            for o in db_session.query(Orcamento)
            .filter(criterio_departamento(Orcamento.departamento_id, db_session, tes))
            .all()
        }
        assert ids == {"TES"}

    def test_corporativo_inclui_documento_sem_departamento(self, db_session):
        _, _, corp = _depts_leitura(db_session)
        db_session.add_all(
            [
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=None, descricao="NULL"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=corp.id, descricao="CORP"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=6, descricao="TES"),
            ]
        )
        db_session.commit()
        tes = db_session.query(Departamento).filter(Departamento.id == 6).first()
        ids_corp = {
            o.descricao
            for o in db_session.query(Orcamento)
            .filter(criterio_departamento(Orcamento.departamento_id, db_session, corp))
            .all()
        }
        ids_tes = {
            o.descricao
            for o in db_session.query(Orcamento)
            .filter(criterio_departamento(Orcamento.departamento_id, db_session, tes))
            .all()
        }
        assert ids_corp == {"NULL", "CORP"}
        assert "TES" not in ids_corp
        assert ids_tes == {"TES"}

    def test_todos_soma_cada_documento_uma_vez(self, db_session):
        tes, mkt, corp = _depts_leitura(db_session)
        db_session.add_all(
            [
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=mkt.id, descricao="MKT"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=tes.id, descricao="TES"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=corp.id, descricao="CORP"),
                Orcamento(ano=2026, tipo="DESPESAS", departamento_id=None, descricao="NULL"),
            ]
        )
        db_session.commit()
        todos = departamento_sentinela_todos()
        assert todos.id == DEPARTAMENTO_TODOS_ID
        rows = (
            db_session.query(Orcamento)
            .filter(criterio_departamento(Orcamento.departamento_id, db_session, todos))
            .all()
        )
        assert {o.descricao for o in rows} == {"MKT", "TES", "CORP", "NULL"}
        assert len(rows) == 4


class TestPlanosLeitura:
    def test_matriz_vazia_nao_libera_todos_os_planos(self, db_session):
        vazio = Departamento(id=20, nome="Controladoria Vazia")
        p = FinancialPlan(id=30, name="Despesa Comum", tp_conta="R", db_id="2.01")
        db_session.add_all([vazio, p])
        db_session.commit()
        assert 30 not in planos_ids_leitura(db_session, vazio, "D")
        assert planos_ids_leitura(db_session, vazio, "D") == []

    def test_corporativo_ve_todos_os_planos_como_antes(self, db_session):
        tes, mkt, corp = _depts_leitura(db_session)
        p_ex = FinancialPlan(id=31, name="Exclusivo Tes", tp_conta="R", db_id="2.02")
        p_com = FinancialPlan(id=32, name="Comum", tp_conta="R", db_id="2.03")
        p_orf = FinancialPlan(id=33, name="Orfao", tp_conta="R", db_id="2.04")
        db_session.add_all([p_ex, p_com, p_orf])
        db_session.flush()
        db_session.add_all(
            [
                DepartamentoPlano(departamento_id=tes.id, plano_financeiro_id=31, permitido=True),
                DepartamentoPlano(departamento_id=tes.id, plano_financeiro_id=32, permitido=True),
                DepartamentoPlano(departamento_id=mkt.id, plano_financeiro_id=32, permitido=True),
            ]
        )
        db_session.commit()
        ids_corp = planos_ids_leitura(db_session, corp, "D")
        assert 31 in ids_corp and 32 in ids_corp and 33 in ids_corp
        assert 31 in planos_ids_leitura(db_session, tes, "D")
        assert 32 in planos_ids_leitura(db_session, tes, "D")
        assert 33 not in planos_ids_leitura(db_session, tes, "D")

    def test_todos_ve_todos_os_planos_de_despesa(self, db_session):
        p = FinancialPlan(id=34, name="Qualquer D", tp_conta="R", db_id="2.99")
        db_session.add(p)
        db_session.commit()
        ids = planos_ids_leitura(db_session, departamento_sentinela_todos(), "D")
        assert 34 in ids

    def test_leitura_usa_produtos_ativos_mesmo_sem_juncao(self, db_session):
        tes, _, corp = _depts_leitura(db_session)
        extra = CostCenter(id=99, nome="CC extra", status="Ativo")
        db_session.add(extra)
        db_session.commit()
        ids_tes = produtos_ids_leitura(db_session, tes)
        ids_corp = produtos_ids_leitura(db_session, corp)
        assert 1 in ids_tes and 99 in ids_tes
        assert 1 in ids_corp and 99 in ids_corp


class TestParcelaPertence:
    def test_parcela_comum_so_no_departamento_do_name(self, db_session):
        tes, mkt, corp = _depts_leitura(db_session)
        db_session.commit()
        assert parcela_pertence_ao_dept(db_session, "Tesouraria", tes) is True
        assert parcela_pertence_ao_dept(db_session, "Tesouraria", mkt) is False
        assert parcela_pertence_ao_dept(db_session, "Tesouraria", corp) is True
        assert parcela_pertence_ao_dept(db_session, None, corp) is True
        assert parcela_pertence_ao_dept(db_session, None, tes) is False
        todos = departamento_sentinela_todos()
        assert parcela_pertence_ao_dept(db_session, "Tesouraria", todos) is True
        assert parcela_pertence_ao_dept(db_session, None, todos) is True
