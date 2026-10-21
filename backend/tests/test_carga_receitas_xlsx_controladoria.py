from pathlib import Path

from openpyxl import Workbook

from app.models.cost_center import CostCenter
from app.models.departamento import Departamento, DepartamentoPlano
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.carga_orcamento_departamentos_2027 import (
    importar_receitas_xlsx_controladoria,
    ler_aba_receitas_xlsx,
)
from app.services.periodos import MESES_STR


HEADER = [
    "EMPRESA",
    "CÓDIGO",
    "DESCRIÇÃO",
    "CONTA",
    "DESCRIÇÃO CONTA",
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
    "2027",
    "observação",
]


def _planilha(path: Path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Receitas"
    ws.append(HEADER)
    for row in rows:
        ws.append(row)
    wb.save(path)


def _linha(codigo, conta, plano, meses, descricao="X"):
    vals = [meses.get(m) for m in MESES_STR]
    total = sum(v or 0 for v in vals)
    return ["EMP", codigo, descricao, conta, plano] + vals + [total, ""]


def _autorizar(db, dept_id, plano_id):
    db.add(DepartamentoPlano(departamento_id=dept_id, plano_financeiro_id=plano_id, permitido=True))
    db.commit()


def test_le_codigo_e_descricao_conta_receita(tmp_path):
    path = tmp_path / "Receitas.xlsx"
    _planilha(
        path,
        [_linha("10100", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 10, "fev": None})],
    )
    rows, err = ler_aba_receitas_xlsx(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["empreendimento"] == "10100"
    assert rows[0]["plano_financeiro"] == "Receita de Venda de Lotes"
    assert rows[0]["jan"] == 10.0
    assert rows[0]["fev"] == 0.0


def test_ignora_conta_de_despesa(tmp_path):
    path = tmp_path / "Receitas.xlsx"
    _planilha(
        path,
        [
            _linha("10100", "2.05.01.05", "Despesas Bancárias", {"jan": 99}),
            _linha("10100", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 10}),
        ],
    )
    rows, err = ler_aba_receitas_xlsx(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["plano_financeiro"] == "Receita de Venda de Lotes"


def test_soma_duplicata_e_cria_rascunho_receitas(db_session, tmp_path):
    ctrl = Departamento(nome="Controladoria")
    db_session.add(ctrl)
    db_session.commit()
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "10100"
    p1 = db_session.query(FinancialPlan).filter_by(id=1).one()
    p1.name = "Receita de Venda de Lotes"
    p1.db_id = "1010101"
    db_session.commit()
    _autorizar(db_session, ctrl.id, 1)

    path = tmp_path / "Receitas.xlsx"
    _planilha(
        path,
        [
            _linha("10100", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 10}),
            _linha("10100", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 5, "fev": 2}),
        ],
    )
    rel = importar_receitas_xlsx_controladoria(
        db_session, usuario_id=1, gravar=True, path=str(path)
    )
    assert rel["gravado"] is True
    assert rel["total_erros"] == 0
    assert rel["total_validas"] == 1
    assert rel["tipo"] == "RECEITAS"
    orc = db_session.query(Orcamento).filter_by(ano=2027, tipo="RECEITAS", departamento_id=ctrl.id).one()
    item = db_session.query(OrcamentoItem).filter_by(orcamento_id=orc.id).one()
    assert item.jan == 15.0
    assert item.fev == 2.0
    assert item.total_anual == 17.0
    assert db_session.query(Orcamento).filter_by(tipo="DESPESAS").count() == 0


def test_plano_despesa_nao_grava(db_session, tmp_path):
    ctrl = Departamento(nome="Controladoria")
    db_session.add(ctrl)
    db_session.commit()
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "10100"
    p1 = db_session.query(FinancialPlan).filter_by(id=1).one()
    p1.name = "Despesas Bancárias"
    p1.db_id = "2050105"
    db_session.commit()
    _autorizar(db_session, ctrl.id, 1)
    path = tmp_path / "Receitas.xlsx"
    _planilha(
        path,
        [_linha("10100", "1.01.01.01", "Despesas Bancárias", {"jan": 10})],
    )
    rel = importar_receitas_xlsx_controladoria(
        db_session, usuario_id=1, gravar=True, path=str(path)
    )
    assert rel["gravado"] is False
    assert any(e["codigo"] == "V04" for e in rel["erros"])
    assert db_session.query(Orcamento).filter_by(tipo="RECEITAS").count() == 0


def test_codigo_inexistente_nao_grava_receita(db_session, tmp_path):
    ctrl = Departamento(nome="Controladoria")
    db_session.add(ctrl)
    db_session.commit()
    p1 = db_session.query(FinancialPlan).filter_by(id=1).one()
    p1.name = "Receita de Venda de Lotes"
    p1.db_id = "1010101"
    db_session.commit()
    _autorizar(db_session, ctrl.id, 1)
    path = tmp_path / "Receitas.xlsx"
    _planilha(
        path,
        [_linha("99999", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 10})],
    )
    rel = importar_receitas_xlsx_controladoria(
        db_session, usuario_id=1, gravar=True, path=str(path)
    )
    assert rel["gravado"] is False
    assert any(e["codigo"] == "V02" for e in rel["erros"])
    assert db_session.query(OrcamentoItem).count() == 0
