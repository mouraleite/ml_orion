"""Passo 5: conferência — conta comum, exclusivo Controladoria, Todos = soma sem duplicar."""
from datetime import date

from app.api.routes.acompanhamento import get_acompanhamento_despesas
from app.models.actual_transaction import ActualTransaction
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.user import User
from app.services.departamento_leitura import departamento_sentinela_todos


def _item(itens, plano_id):
    return next((i for i in itens if i["plano_financeiro_id"] == plano_id), None)


def _total_orcado(data):
    return round(sum(i["orcado"]["total"] for i in data.get("itens", [])), 2)


def _total_realizado(data):
    return round(sum(i["realizado"]["total"] for i in data.get("itens", [])), 2)


def test_conferencia_comum_exclusivo_e_todos(db_session):
    tes = Departamento(id=6, nome="Tesouraria")
    ctrl = Departamento(id=3, nome="Controladoria")
    corp = Departamento(id=18, nome="Corporativo", is_residual=True)
    p_com = FinancialPlan(id=50, name="Conta Comum Conf", tp_conta="R", db_id="2.50")
    p_ex = FinancialPlan(id=51, name="Exclusivo Controladoria Conf", tp_conta="R", db_id="2.51")
    db_session.add_all([tes, ctrl, corp, p_com, p_ex])
    db_session.flush()
    mkt = db_session.query(Departamento).filter(Departamento.id == 1).first()
    db_session.add_all(
        [
            DepartamentoPlano(departamento_id=tes.id, plano_financeiro_id=50, permitido=True),
            DepartamentoPlano(departamento_id=mkt.id, plano_financeiro_id=50, permitido=True),
            DepartamentoPlano(departamento_id=ctrl.id, plano_financeiro_id=51, permitido=True),
            ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=50, permitido=True),
            ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=51, permitido=True),
        ]
    )

    def _orc(dept_id, plano_id, jan, descricao):
        o = Orcamento(
            ano=2060,
            tipo="DESPESAS",
            status="Aprovado",
            departamento_id=dept_id,
            descricao=descricao,
            produto_id=1,
        )
        db_session.add(o)
        db_session.flush()
        db_session.add(
            OrcamentoItem(
                orcamento_id=o.id,
                produto_id=1,
                plano_financeiro_id=plano_id,
                jan=jan,
                total_anual=jan,
            )
        )
        return o

    _orc(mkt.id, 50, 100.0, "MKT")
    _orc(tes.id, 50, 40.0, "TES")
    _orc(ctrl.id, 51, 80.0, "CTRL")
    _orc(corp.id, 50, 10.0, "CORP")

    def _parcela(source, plano_name, valor, auth):
        db_session.add(
            ActualTransaction(
                cost_center_id=1,
                source_id=source,
                transaction_type="OUTCOME",
                category=plano_name,
                transaction_date=date(2060, 1, 10),
                value=valor,
                is_forecast=False,
                authorization_name=auth,
            )
        )

    _parcela("OUT-5001-OP1-PMT-1-DT-20600110-FC-1", p_com.name, 30.0, "Marketing")
    _parcela("OUT-5002-OP1-PMT-1-DT-20600110-FC-1", p_com.name, 20.0, "Tesouraria")
    _parcela("OUT-5003-OP1-PMT-1-DT-20600110-FC-1", p_ex.name, 15.0, "Controladoria")
    _parcela("OUT-5004-OP1-PMT-1-DT-20600110-FC-1", p_com.name, 5.0, None)
    db_session.commit()

    user = db_session.query(User).filter(User.id == 1).first()
    tes = db_session.query(Departamento).filter(Departamento.id == 6).first()
    ctrl = db_session.query(Departamento).filter(Departamento.id == 3).first()
    mkt = db_session.query(Departamento).filter(Departamento.id == 1).first()
    corp = db_session.query(Departamento).filter(Departamento.id == 18).first()

    d_tes = get_acompanhamento_despesas(2060, False, False, db_session, tes, user)
    d_ctrl = get_acompanhamento_despesas(2060, False, False, db_session, ctrl, user)
    d_mkt = get_acompanhamento_despesas(2060, False, False, db_session, mkt, user)
    d_corp = get_acompanhamento_despesas(2060, False, False, db_session, corp, user)
    d_todos = get_acompanhamento_despesas(
        2060, False, False, db_session, departamento_sentinela_todos(), user
    )

    comum_tes = _item(d_tes["itens"], 50)
    comum_mkt = _item(d_mkt["itens"], 50)
    comum_ctrl = _item(d_ctrl["itens"], 50)
    ex_tes = _item(d_tes["itens"], 51)
    ex_ctrl = _item(d_ctrl["itens"], 51)
    comum_todos = _item(d_todos["itens"], 50)
    ex_todos = _item(d_todos["itens"], 51)
    comum_corp = _item(d_corp["itens"], 50)

    assert comum_tes["orcado"]["jan"] == 40.0
    assert comum_tes["realizado"]["jan"] == 20.0
    assert comum_mkt["orcado"]["jan"] == 100.0
    assert comum_mkt["realizado"]["jan"] == 30.0
    assert comum_ctrl is None
    assert ex_tes is None
    assert ex_ctrl["orcado"]["jan"] == 80.0
    assert ex_ctrl["realizado"]["jan"] == 15.0
    assert comum_corp["orcado"]["jan"] == 10.0
    assert comum_corp["realizado"]["jan"] == 55.0

    assert comum_todos["orcado"]["jan"] == 150.0
    assert comum_todos["realizado"]["jan"] == 55.0
    assert ex_todos["orcado"]["jan"] == 80.0
    assert ex_todos["realizado"]["jan"] == 15.0

    assert _total_orcado(d_todos) == round(
        _total_orcado(d_tes) + _total_orcado(d_mkt) + _total_orcado(d_ctrl) + _total_orcado(d_corp),
        2,
    )
    assert _total_realizado(d_todos) == 70.0
    assert _total_realizado(d_corp) == _total_realizado(d_todos)
    assert _total_realizado(d_todos) == round(
        _total_realizado(d_tes)
        + _total_realizado(d_mkt)
        + _total_realizado(d_ctrl)
        + 5.0,
        2,
    )


def test_plano_nao_atrelado_nao_aparece_no_departamento(db_session):
    eng = Departamento(id=22, nome="Engenharia Isolada")
    p_obra = FinancialPlan(id=56, name="Obra Isolada Conf", tp_conta="R", db_id="2.56")
    p_irpj = FinancialPlan(id=55, name="IRPJ Isolado Conf", tp_conta="R", db_id="2.55")
    db_session.add_all([eng, p_obra, p_irpj])
    db_session.flush()
    db_session.add(
        DepartamentoPlano(departamento_id=eng.id, plano_financeiro_id=56, permitido=True)
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="OUT-9001-OP1-PMT-1-DT-20600110-FC-1",
            transaction_type="OUTCOME",
            category=p_irpj.name,
            transaction_date=date(2060, 1, 10),
            value=500.0,
            is_forecast=False,
            authorization_name="Engenharia Isolada",
        )
    )
    db_session.add(
        ActualTransaction(
            cost_center_id=1,
            source_id="OUT-9002-OP1-PMT-1-DT-20600110-FC-1",
            transaction_type="OUTCOME",
            category=p_obra.name,
            transaction_date=date(2060, 1, 10),
            value=80.0,
            is_forecast=False,
            authorization_name="Engenharia Isolada",
        )
    )
    db_session.commit()

    user = db_session.query(User).filter(User.id == 1).first()
    eng = db_session.query(Departamento).filter(Departamento.id == 22).first()
    data = get_acompanhamento_despesas(2060, False, False, db_session, eng, user)
    assert _item(data["itens"], 55) is None
    obra = _item(data["itens"], 56)
    assert obra is not None
    assert obra["realizado"]["jan"] == 80.0
