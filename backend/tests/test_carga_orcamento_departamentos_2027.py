"""Carga 2027 por departamento a partir da aba fImportacao."""
from pathlib import Path

from openpyxl import Workbook

from app.models.cost_center import CostCenter
from app.models.departamento import Departamento, DepartamentoPlano
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.carga_orcamento_departamentos_2027 import (
    importar_orcamentos_departamentos_2027,
    ler_aba_fimportacao,
)
from app.services.periodos import MESES_STR


def _planilha(path: Path, rows):
    wb = Workbook()
    wb.active.title = "Orçamento"
    ws = wb.create_sheet("fImportacao")
    header = (
        ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        + ["Total", "Média", "Empreendimento", "Produto", "Plano Financeiro", "Empresa"]
    )
    ws.append(header)
    for row in rows:
        ws.append(row)
    wb.save(path)


def _linha(emp, plano, meses, produto="X"):
    vals = [meses.get(m) for m in MESES_STR]
    total = sum(v or 0 for v in vals)
    return vals + [total, None, emp, produto, plano, "0001 - MLDU"]


def _arvore(tmp: Path, pasta: str, nome_arquivo: str, rows):
    dest = tmp / pasta / "2027"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / nome_arquivo
    _planilha(path, rows)
    return path


def _autorizar(db, dept_id, produto_id, plano_id):
    db.add(DepartamentoPlano(departamento_id=dept_id, plano_financeiro_id=plano_id, permitido=True))
    db.commit()


def test_le_fimportacao_nao_aba_ativa(tmp_path):
    path = tmp_path / "arq.xlsm"
    wb = Workbook()
    wb.active.title = "Orçamento"
    wb.active.append(["não é esta"])
    ws = wb.create_sheet("fImportacao")
    ws.append(
        ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        + ["Total", "Média", "Empreendimento", "Produto", "Plano Financeiro", "Empresa"]
    )
    ws.append(_linha("70127", "Conselho", {"fev": 10, "abr": 20}))
    wb.save(path)
    rows, err = ler_aba_fimportacao(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["empreendimento"] == "70127"
    assert rows[0]["jan"] == 0.0
    assert rows[0]["fev"] == 10.0
    assert rows[0]["abr"] == 20.0


def test_carga_por_departamento_como_usuario(db_session, tmp_path):
    tesouraria = Departamento(id=6, nome="Tesouraria")
    db_session.add(tesouraria)
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "70127"
    db_session.commit()
    _autorizar(db_session, 6, 1, 1)

    _arvore(
        tmp_path,
        "Pagadoria",
        "Orçamento - Pagadoria - Importação.xlsm",
        [
            _linha("70127", "Plano Fin 1", {"jan": 100, "fev": None}),
            _linha("70127", "Plano Fin 1", {"jan": 50, "mar": 7}),
        ],
    )
    _arvore(
        tmp_path,
        "SDR",
        "Orçamento - SDR.xlsm",
        [_linha("70127", "Plano Fin 1", {"jan": 999})],
    )
    _arvore(
        tmp_path,
        "Materiais",
        "Base para importação - 2027.xlsm",
        [_linha("70127", "Plano Fin 1", {"jan": 888})],
    )
    _arvore(
        tmp_path,
        "Marketing",
        "Orçamento - Marketing - Importação.xlsm",
        [_linha("70127", "Plano Fin 1", {"jun": 30})],
    )
    _autorizar(db_session, 1, 1, 1)

    rel = importar_orcamentos_departamentos_2027(
        db_session, usuario_id=1, gravar=True, base_dir=str(tmp_path)
    )
    assert rel["erro_base"] is None
    nomes = {d["departamento"] for d in rel["departamentos"]}
    assert "Tesouraria" in nomes
    assert "Marketing" in nomes
    ignorados = {i["pasta"] for i in rel["ignorados"]}
    assert "Materiais" in ignorados
    assert "SDR" not in {d["pasta"] for d in rel["departamentos"]}

    tes = db_session.query(Orcamento).filter_by(ano=2027, tipo="DESPESAS", departamento_id=6).one()
    item = db_session.query(OrcamentoItem).filter_by(orcamento_id=tes.id).one()
    assert item.produto_id == 1
    assert item.jan == 150.0
    assert item.fev == 0.0
    assert item.mar == 7.0
    assert item.total_anual == 157.0

    mkt = db_session.query(Orcamento).filter_by(ano=2027, tipo="DESPESAS", departamento_id=1).one()
    assert mkt.departamento_id == 1
    mkt_item = db_session.query(OrcamentoItem).filter_by(orcamento_id=mkt.id).one()
    assert mkt_item.jun == 30.0


def test_codigo_inexistente_nao_inventa_nem_grava(db_session, tmp_path):
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "70127"
    db_session.commit()
    _autorizar(db_session, 1, 1, 1)
    _arvore(
        tmp_path,
        "Marketing",
        "Orçamento - Marketing - Importação.xlsm",
        [_linha("99999", "Plano Fin 1", {"jan": 10})],
    )
    rel = importar_orcamentos_departamentos_2027(
        db_session, usuario_id=1, gravar=True, base_dir=str(tmp_path)
    )
    mkt = [d for d in rel["departamentos"] if d["departamento"] == "Marketing"][0]
    assert mkt["gravado"] is False
    assert any(e["codigo"] == "V02" for e in mkt["erros"])
    assert db_session.query(Orcamento).filter_by(ano=2027, departamento_id=1).count() == 0


def test_linha_zerada_nao_bloqueia_matriz(db_session, tmp_path):
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "70127"
    db_session.commit()
    _autorizar(db_session, 1, 1, 1)
    _arvore(
        tmp_path,
        "Marketing",
        "Orçamento - Marketing - Importação.xlsm",
        [
            _linha("70127", "Plano Fin 2", {}),
            _linha("70127", "Plano Fin 1", {"jan": 10}),
        ],
    )
    rel = importar_orcamentos_departamentos_2027(
        db_session, usuario_id=1, gravar=True, base_dir=str(tmp_path)
    )
    mkt = [d for d in rel["departamentos"] if d["departamento"] == "Marketing"][0]
    assert mkt["gravado"] is True
    assert mkt["total_erros"] == 0
    item = db_session.query(OrcamentoItem).one()
    assert item.jan == 10.0


def test_simulacao_nao_grava(db_session, tmp_path):
    cc = db_session.query(CostCenter).filter_by(id=1).one()
    cc.id_sienge = "70127"
    db_session.commit()
    _autorizar(db_session, 1, 1, 1)
    _arvore(
        tmp_path,
        "Marketing",
        "Orçamento - Marketing - Importação.xlsm",
        [_linha("70127", "Plano Fin 1", {"jan": 10})],
    )
    rel = importar_orcamentos_departamentos_2027(
        db_session, usuario_id=1, gravar=False, base_dir=str(tmp_path)
    )
    assert rel["gravado"] is False
    assert db_session.query(Orcamento).filter_by(ano=2027).count() == 0
    mkt = [d for d in rel["departamentos"] if d["departamento"] == "Marketing"][0]
    assert mkt["total_validas"] == 1
