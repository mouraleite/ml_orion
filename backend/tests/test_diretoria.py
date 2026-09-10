"""Diretoria: vários depts; um dept em no máximo uma diretoria; leitura agregada."""
from datetime import date

from app.api.routes.acompanhamento import get_acompanhamento_despesas
from app.models.actual_transaction import ActualTransaction
from app.models.departamento import Departamento, DepartamentoPlano, Diretoria, ProdutoPlanoFinanceiro
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.user import User
from app.services.departamento_leitura import (
    criterio_departamento,
    departamento_sentinela_diretoria,
    eh_diretoria,
    planos_ids_leitura,
    rejeitar_gravacao_contexto,
)


def test_dept_nao_pode_estar_em_duas_diretorias(db_session):
    d1 = Diretoria(nome="Operações")
    d2 = Diretoria(nome="Financeira")
    db_session.add_all([d1, d2])
    db_session.flush()
    eng = Departamento(id=40, nome="Engenharia Dir", diretoria_id=d1.id)
    db_session.add(eng)
    db_session.commit()
    eng.diretoria_id = d2.id
    db_session.flush()
    assert eng.diretoria_id == d2.id
    assert db_session.query(Departamento).filter(Departamento.diretoria_id == d1.id).count() == 0


def test_sentinela_diretoria_e_criterio(db_session):
    di = Diretoria(nome="Ops")
    db_session.add(di)
    db_session.flush()
    a = Departamento(id=41, nome="A Ops", diretoria_id=di.id)
    b = Departamento(id=42, nome="B Ops", diretoria_id=di.id)
    c = Departamento(id=43, nome="Fora")
    db_session.add_all([a, b, c])
    db_session.add_all(
        [
            Orcamento(ano=2070, tipo="DESPESAS", departamento_id=41, descricao="A"),
            Orcamento(ano=2070, tipo="DESPESAS", departamento_id=42, descricao="B"),
            Orcamento(ano=2070, tipo="DESPESAS", departamento_id=43, descricao="C"),
        ]
    )
    db_session.commit()
    sent = departamento_sentinela_diretoria(db_session, di.id)
    assert eh_diretoria(sent)
    assert sent.id == -di.id
    rows = (
        db_session.query(Orcamento)
        .filter(
            Orcamento.ano == 2070,
            criterio_departamento(Orcamento.departamento_id, db_session, sent),
        )
        .all()
    )
    assert {o.descricao for o in rows} == {"A", "B"}


def test_planos_leitura_une_matrizes_dos_membros(db_session):
    di = Diretoria(nome="Ops Planos")
    db_session.add(di)
    db_session.flush()
    a = Departamento(id=44, nome="A Plan", diretoria_id=di.id)
    b = Departamento(id=45, nome="B Plan", diretoria_id=di.id)
    p1 = FinancialPlan(id=401, name="P1 Dir", tp_conta="R", db_id="2.91")
    p2 = FinancialPlan(id=402, name="P2 Dir", tp_conta="R", db_id="2.92")
    db_session.add_all([a, b, p1, p2])
    db_session.flush()
    db_session.add_all(
        [
            DepartamentoPlano(departamento_id=44, plano_financeiro_id=401, permitido=True),
            DepartamentoPlano(departamento_id=45, plano_financeiro_id=402, permitido=True),
        ]
    )
    db_session.commit()
    sent = departamento_sentinela_diretoria(db_session, di.id)
    ids = set(planos_ids_leitura(db_session, sent, "D"))
    assert 401 in ids and 402 in ids


def test_gravacao_bloqueada_em_diretoria():
    from fastapi import HTTPException

    sent = type("S", (), {"id": -1, "nome": "X"})()
    try:
        rejeitar_gravacao_contexto(sent, "POST")
        assert False, "deveria bloquear"
    except HTTPException as e:
        assert e.status_code == 400


def test_acompanhamento_diretoria_soma_membros(db_session):
    di = Diretoria(nome="Ops Acomp")
    db_session.add(di)
    db_session.flush()
    mkt = db_session.query(Departamento).filter(Departamento.id == 1).first()
    a = Departamento(id=46, nome="Tesouraria Dir", diretoria_id=di.id)
    mkt.diretoria_id = di.id
    p = FinancialPlan(id=403, name="Conta Dir Comum", tp_conta="R", db_id="2.93")
    db_session.add_all([a, p])
    db_session.flush()
    db_session.add_all(
        [
            DepartamentoPlano(departamento_id=46, plano_financeiro_id=403, permitido=True),
            DepartamentoPlano(departamento_id=1, plano_financeiro_id=403, permitido=True),
            ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=403, permitido=True),
        ]
    )

    def _orc(dept_id, jan, desc):
        o = Orcamento(
            ano=2071,
            tipo="DESPESAS",
            status="Aprovado",
            departamento_id=dept_id,
            descricao=desc,
            produto_id=1,
        )
        db_session.add(o)
        db_session.flush()
        db_session.add(
            OrcamentoItem(
                orcamento_id=o.id,
                produto_id=1,
                plano_financeiro_id=403,
                jan=jan,
                total_anual=jan,
            )
        )

    _orc(46, 40.0, "TES")
    _orc(1, 60.0, "MKT")
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="OUT-7001-OP1-PMT-1-DT-20710110-FC-1",
            transaction_type="OUTCOME",
            category=p.name,
            transaction_date=date(2071, 1, 10),
            value=25.0,
            is_forecast=False,
            authorization_name="Marketing",
        )
    )
    db_session.commit()

    user = db_session.query(User).filter(User.id == 1).first()
    sent = departamento_sentinela_diretoria(db_session, di.id)
    data = get_acompanhamento_despesas(2071, False, False, db_session, sent, user)
    item = next(i for i in data["itens"] if i["plano_financeiro_id"] == 403)
    assert item["orcado"]["jan"] == 100.0
    assert item["realizado"]["jan"] == 25.0


def test_diretoria_orcado_fallback_corporativo(db_session):
    """Carga só no residual: diretoria lê Corporativo filtrado pelos planos dos membros."""
    from app.models.departamento import DepartamentoPlano, ProdutoPlanoFinanceiro

    corp = db_session.query(Departamento).filter(Departamento.id == 18).first()
    if corp is None:
        corp = Departamento(id=18, nome="Corporativo", is_residual=True, ativo=True)
        db_session.add(corp)
        db_session.flush()
    else:
        corp.is_residual = True

    di = Diretoria(nome="Comercial Fallback")
    db_session.add(di)
    db_session.flush()
    vendas = Departamento(id=47, nome="Vendas Fallback", diretoria_id=di.id)
    p_ok = FinancialPlan(id=404, name="Plano Coml", tp_conta="R", db_id="2.94")
    p_out = FinancialPlan(id=405, name="Plano Outro", tp_conta="R", db_id="2.95")
    db_session.add_all([vendas, p_ok, p_out])
    db_session.flush()
    db_session.add_all(
        [
            DepartamentoPlano(departamento_id=47, plano_financeiro_id=404, permitido=True),
            ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=404, permitido=True),
            ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=405, permitido=True),
        ]
    )
    o = Orcamento(
        ano=2072,
        tipo="DESPESAS",
        status="Aprovado",
        departamento_id=18,
        descricao="CORP FB",
        produto_id=1,
    )
    db_session.add(o)
    db_session.flush()
    db_session.add_all(
        [
            OrcamentoItem(
                orcamento_id=o.id,
                produto_id=1,
                plano_financeiro_id=404,
                jan=80.0,
                total_anual=80.0,
            ),
            OrcamentoItem(
                orcamento_id=o.id,
                produto_id=1,
                plano_financeiro_id=405,
                jan=999.0,
                total_anual=999.0,
            ),
        ]
    )
    db_session.commit()

    user = db_session.query(User).filter(User.id == 1).first()
    sent = departamento_sentinela_diretoria(db_session, di.id)
    data = get_acompanhamento_despesas(2072, False, False, db_session, sent, user)
    by_plano = {i["plano_financeiro_id"]: i for i in data["itens"]}
    assert 404 in by_plano
    assert by_plano[404]["orcado"]["jan"] == 80.0
    assert 405 not in by_plano
