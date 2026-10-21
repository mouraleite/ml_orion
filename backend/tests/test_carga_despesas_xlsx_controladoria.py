from pathlib import Path

from openpyxl import Workbook

from app.models.cost_center import CostCenter
from app.models.departamento import Departamento, DepartamentoPlano
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.budget_shared import DESCRICAO_DOCUMENTO_ORCAMENTO
from app.services.carga_orcamento_departamentos_2027 import (
    importar_despesas_xlsx_controladoria,
    ler_aba_despesas_xlsx,
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
    ws.title = "Despesas"
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


def test_le_codigo_e_descricao_conta(tmp_path):
    path = tmp_path / "Despesas.xlsx"
    _planilha(
        path,
        [_linha("10100", "2.05.01.05", "Despesas Bancárias", {"jan": 10, "fev": None})],
    )
    rows, err = ler_aba_despesas_xlsx(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["empreendimento"] == "10100"
    assert rows[0]["plano_financeiro"] == "Despesas Bancárias"
    assert rows[0]["jan"] == 10.0
    assert rows[0]["fev"] == 0.0


def test_ignora_conta_de_receita(tmp_path):
    path = tmp_path / "Despesas.xlsx"
    _planilha(
        path,
        [
            _linha("10100", "1.01.01.01", "Receita de Venda de Lotes", {"jan": 99}),
            _linha("10100", "2.05.01.05", "Despesas Bancárias", {"jan": 10}),
        ],
    )
    rows, err = ler_aba_despesas_xlsx(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["plano_financeiro"] == "Despesas Bancárias"


def test_soma_duplicata_e_nao_apaga_item_existente(db_session, tmp_path):
    ctrl = Departamento(nome="Controladoria")
    db_session.add(ctrl)
    db_session.commit()
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "10100"
    p1 = db_session.query(FinancialPlan).filter_by(id=1).one()
    p1.name = "Despesas Bancárias"
    p2 = db_session.query(FinancialPlan).filter_by(id=2).one()
    p2.name = "Consultorias Diversas"
    db_session.commit()
    _autorizar(db_session, ctrl.id, 1)
    _autorizar(db_session, ctrl.id, 2)

    orc = Orcamento(
        descricao=DESCRICAO_DOCUMENTO_ORCAMENTO,
        ano=2027,
        tipo="DESPESAS",
        status="Rascunho",
        departamento_id=ctrl.id,
        usuario_criador_id=1,
        versao_numero=1,
    )
    db_session.add(orc)
    db_session.flush()
    db_session.add(
        OrcamentoItem(
            orcamento_id=orc.id,
            produto_id=1,
            plano_financeiro_id=2,
            jan=100.0,
            total_anual=100.0,
        )
    )
    db_session.commit()

    path = tmp_path / "Despesas.xlsx"
    _planilha(
        path,
        [
            _linha("10100", "2.05.01.05", "Despesas Bancárias", {"jan": 10}),
            _linha("10100", "2.05.01.05", "Despesas Bancárias", {"jan": 5, "fev": 2}),
        ],
    )
    rel = importar_despesas_xlsx_controladoria(
        db_session, usuario_id=1, gravar=True, path=str(path)
    )
    assert rel["gravado"] is True
    assert rel["total_erros"] == 0
    assert rel["total_validas"] == 1
    itens = db_session.query(OrcamentoItem).filter_by(orcamento_id=orc.id).all()
    assert len(itens) == 2
    legado = [i for i in itens if i.plano_financeiro_id == 2][0]
    assert legado.jan == 100.0
    novo = [i for i in itens if i.plano_financeiro_id == 1][0]
    assert novo.jan == 15.0
    assert novo.fev == 2.0
    assert novo.total_anual == 17.0


def test_codigo_inexistente_nao_grava(db_session, tmp_path):
    ctrl = Departamento(nome="Controladoria")
    db_session.add(ctrl)
    db_session.commit()
    _autorizar(db_session, ctrl.id, 1)
    path = tmp_path / "Despesas.xlsx"
    _planilha(
        path,
        [_linha("99999", "2.05.01.05", "Plano Fin 1", {"jan": 10})],
    )
    rel = importar_despesas_xlsx_controladoria(
        db_session, usuario_id=1, gravar=True, path=str(path)
    )
    assert rel["gravado"] is False
    assert any(e["codigo"] == "V02" for e in rel["erros"])
    assert db_session.query(OrcamentoItem).count() == 0
