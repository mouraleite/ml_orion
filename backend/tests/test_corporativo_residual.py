"""Corporativo (ex-Consolidado - Sienge): residual da matriz, sem mudar filtro de tela."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.departamento import Departamento, DepartamentoPlano
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento
from app.services.corporativo import (
    CORPORATIVO_NOME,
    classificar_planos_matriz,
    eh_corporativo,
    ensure_corporativo_departamento,
    resumo_residual,
)
from app.services.depara_autorizacao import sugerir_departamento_id


class TestEhCorporativo:
    def test_nome_novo_e_legado(self):
        assert eh_corporativo("Corporativo") is True
        assert eh_corporativo("Consolidado - Sienge") is True
        assert eh_corporativo("Tesouraria") is False
        assert eh_corporativo("Consolidado (Todas as Obras)") is False


class TestEnsureCorporativo:
    def test_renomeia_consolidado_sienge(self, db_session):
        legado = Departamento(id=18, nome="Consolidado - Sienge", ativo=True)
        db_session.add(legado)
        db_session.commit()

        dept = ensure_corporativo_departamento(db_session)
        assert dept.id == 18
        assert dept.nome == CORPORATIVO_NOME
        assert bool(dept.is_residual) is True

        again = ensure_corporativo_departamento(db_session)
        assert again.id == 18

    def test_depara_nao_mapeia_para_corporativo(self, db_session):
        depts = [
            {"id": 6, "nome": "Tesouraria"},
            {"id": 18, "nome": "Corporativo"},
        ]
        assert sugerir_departamento_id("Corporativo", depts) is None
        assert sugerir_departamento_id("Consolidado - Sienge", depts) is None
        assert sugerir_departamento_id("Tesouraria", depts) == 6


class TestClassificarPlanos:
    def test_exclusivo_comum_e_sem_matriz(self, db_session):
        tes = Departamento(id=6, nome="Tesouraria")
        mkt = Departamento(id=11, nome="Marketing")
        corp = Departamento(id=18, nome="Corporativo", is_residual=True)
        p_ex = FinancialPlan(id=10, name="Exclusivo Ctrl")
        p_com = FinancialPlan(id=11, name="Comum")
        p_orf = FinancialPlan(id=12, name="Orfao")
        db_session.add_all([tes, mkt, corp, p_ex, p_com, p_orf])
        db_session.flush()
        db_session.add_all(
            [
                DepartamentoPlano(departamento_id=6, plano_financeiro_id=10, permitido=True),
                DepartamentoPlano(departamento_id=6, plano_financeiro_id=11, permitido=True),
                DepartamentoPlano(departamento_id=11, plano_financeiro_id=11, permitido=True),
                DepartamentoPlano(departamento_id=18, plano_financeiro_id=12, permitido=True),
            ]
        )
        db_session.commit()

        classes = classificar_planos_matriz(db_session)
        assert classes[10] == "exclusivo"
        assert classes[11] == "comum"
        assert classes[12] == "residual"
        assert classes.get(1) == "exclusivo"  # mock conftest: dept 1 × plano 1

        resumo = resumo_residual(db_session)
        assert resumo["departamento_id"] == 18
        assert resumo["nome"] == CORPORATIVO_NOME
        assert resumo["planos_residuais"] >= 1
        assert resumo["planos_comuns"] >= 1
        assert resumo["planos_exclusivos"] >= 1

    def test_orcamento_sem_departamento_conta_residual(self, db_session):
        ensure_corporativo_departamento(db_session)
        db_session.add(
            Orcamento(
                descricao="Sem dono",
                ano=2026,
                tipo="DESPESAS",
                status="Rascunho",
                departamento_id=None,
                versao_numero=1,
            )
        )
        db_session.commit()
        resumo = resumo_residual(db_session)
        assert resumo["orcamentos_sem_departamento"] >= 1
