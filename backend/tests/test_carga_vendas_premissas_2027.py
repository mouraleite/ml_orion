from pathlib import Path

from openpyxl import Workbook

from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.payment_plan import PaymentPlan
from app.services.carga_orcamento_vendas_premissas_2027 import (
    importar_vendas_premissas_2027,
    ler_premissas_comerciais,
)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MIX = ["A VISTA", 24, 36, 48, 60, 120, 180]


def _bloco(ws, start_row: int, ano, soma_meses, mix_map):
    ws.cell(start_row, 2, "PERIODO")
    for i, nome in enumerate(MESES, start=3):
        ws.cell(start_row, i, nome)
    ws.cell(start_row, 15, ano)
    ws.cell(start_row + 1, 2, "SOMA DOS PERIODOS")
    for i, v in enumerate(soma_meses, start=3):
        ws.cell(start_row + 1, i, v)
    ws.cell(start_row + 1, 15, sum(soma_meses))
    for off, lab in enumerate(MIX):
        row = start_row + 2 + off
        ws.cell(row, 2, lab)
        vals = mix_map.get(str(lab), [0] * 12)
        for i, v in enumerate(vals, start=3):
            ws.cell(row, i, v)
        ws.cell(row, 15, sum(vals))


def _aba_produto(wb, titulo, cidade, nome, ticket, *, m3_label=None, ano=2027, mix_map=None):
    ws = wb.create_sheet(titulo)
    ws["C3"] = cidade
    ws["C4"] = nome
    if m3_label:
        ws["M3"] = m3_label
        ws["M4"] = ticket
    else:
        ws["M3"] = ticket
    mix_map = mix_map or {"36": [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]}
    soma = [0] * 12
    for vals in mix_map.values():
        for i, v in enumerate(vals):
            soma[i] += v
    _bloco(ws, 6, ano, soma, mix_map)
    _bloco(ws, 15, 2028, [1] * 12, {"180": [1] * 12})
    return ws


def _planilha(path: Path, produtos):
    wb = Workbook()
    wb.active.title = "HOME"
    wb.create_sheet("PLANOS")
    wb.create_sheet("PREÇOS COMERCIAIS")
    for p in produtos:
        _aba_produto(wb, **p)
    wb.save(path)


def _cadastro(db, sienge="15600", nome_cc="TAGUAI - JARDIM DOS IPÊS III"):
    dept = Departamento(nome="Vendas")
    db.add(dept)
    cc = CostCenter(id_sienge=sienge, nome=nome_cc, status="Ativo")
    db.add(cc)
    for nome in ("À vista", "24x", "36x", "48x", "60x", "120x", "180x"):
        if not db.query(PaymentPlan).filter_by(nome=nome).first():
            db.add(PaymentPlan(nome=nome, condicoes_json=[]))
    db.commit()
    return dept, cc


def test_le_mix_2027_e_ignora_2028(tmp_path):
    path = tmp_path / "premissas.xlsx"
    _planilha(
        path,
        [
            {
                "titulo": "JD IPES III",
                "cidade": "TAGUAI",
                "nome": "JARDIM DOS IPÊS III",
                "ticket": 63000,
                "mix_map": {"36": [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], "A VISTA": [0] * 12},
            }
        ],
    )
    rows, err = ler_premissas_comerciais(str(path))
    assert err is None
    assert {(r["mes"], r["mix"], r["numero_vendas"]) for r in rows} == {
        (1, "36", 2.0),
        (12, "36", 1.0),
    }
    assert all(r["ano"] == 2027 for r in rows)
    assert all(r["ticket_medio"] == 63000 for r in rows)


def test_ticket_vem_de_m4_quando_m3_e_rotulo(tmp_path):
    path = tmp_path / "premissas.xlsx"
    _planilha(
        path,
        [
            {
                "titulo": "LIVIA",
                "cidade": "BOTUCATU",
                "nome": "LIVIA",
                "ticket": 122250,
                "m3_label": "VALOR MÉDIO",
                "mix_map": {"180": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]},
            }
        ],
    )
    rows, err = ler_premissas_comerciais(str(path))
    assert err is None
    assert len(rows) == 1
    assert rows[0]["ticket_medio"] == 122250
    assert rows[0]["mix"] == "180"


def test_grava_rascunho_vendas_com_plano_36x(db_session, tmp_path):
    _cadastro(db_session)
    path = tmp_path / "premissas.xlsx"
    _planilha(
        path,
        [
            {
                "titulo": "JD IPES III",
                "cidade": "TAGUAI",
                "nome": "JARDIM DOS IPÊS III",
                "ticket": 63000,
                "mix_map": {"36": [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]},
            }
        ],
    )
    rel = importar_vendas_premissas_2027(db_session, usuario_id=1, gravar=True, path=str(path))
    assert rel["gravado"] is True
    assert rel["total_erros"] == 0
    assert rel["unidades"] == 3
    assert rel["vgv"] == 189000
    orc = db_session.query(Orcamento).filter_by(ano=2027, tipo="VENDAS").one()
    assert orc.status == "Rascunho"
    assert orc.departamento.nome == "Vendas"
    itens = db_session.query(OrcamentoVendaItem).filter_by(orcamento_id=orc.id).all()
    assert len(itens) == 2
    plano = db_session.query(PaymentPlan).filter_by(nome="36x").one()
    assert {i.mes: i.numero_vendas for i in itens} == {1: 2, 12: 1}
    assert all(i.plano_venda_id == plano.id for i in itens)
    assert all(i.ticket_medio == 63000 for i in itens)


def test_produto_sem_depara_nao_grava(db_session, tmp_path):
    _cadastro(db_session)
    path = tmp_path / "premissas.xlsx"
    _planilha(
        path,
        [
            {
                "titulo": "IGAVETA",
                "cidade": "ARAÇARIGUAMA",
                "nome": "IGAVETÁ",
                "ticket": 100,
                "mix_map": {"36": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
            }
        ],
    )
    rel = importar_vendas_premissas_2027(db_session, usuario_id=1, gravar=True, path=str(path))
    assert rel["gravado"] is False
    assert any(e["codigo"] == "V02" for e in rel["erros"])
    assert db_session.query(Orcamento).filter_by(tipo="VENDAS").count() == 0


def test_aba_sem_venda_2027_nao_gera_linha(tmp_path):
    path = tmp_path / "premissas.xlsx"
    wb = Workbook()
    wb.active.title = "HOME"
    ws = wb.create_sheet("GRANJA")
    ws["C3"] = "ARAÇARIGUAMA"
    ws["C4"] = "GRANJA"
    ws["M3"] = "VALOR MÉDIO"
    _bloco(ws, 6, "digitar ano aqui", [0] * 12, {})
    wb.save(path)
    rows, err = ler_premissas_comerciais(str(path))
    assert err is None
    assert rows == []
