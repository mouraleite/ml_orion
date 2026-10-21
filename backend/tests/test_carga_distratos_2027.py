from pathlib import Path

from openpyxl import Workbook

from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.payment_plan import PaymentPlan
from app.services.carga_orcamento_distratos_2027 import (
    COL_JAN_2027,
    importar_distratos_2027,
    ler_previsao_distratos_2027,
)


def _planilha(path: Path, linhas):
    wb = Workbook()
    ws = wb.active
    ws.title = "TABELA DINAMICA"
    ws["AO5"] = "PREVISÕES DE CANCELAMENTOS"
    ws["B7"] = "Empreendimento "
    for mes in range(12):
        ws.cell(7, COL_JAN_2027 + mes, mes + 1)
    for i, (sienge, nome, meses) in enumerate(linhas, start=8):
        ws.cell(i, 2, f"{sienge} - {nome}")
        for mes, qtd in meses.items():
            ws.cell(i, COL_JAN_2027 + mes - 1, qtd)
    ws.cell(8 + len(linhas), 2, "Total Geral")
    wb.save(path)


def _rascunho_com_venda(db, sienge="17701", ticket=63000):
    dept = Departamento(nome="Vendas")
    db.add(dept)
    cc = CostCenter(id_sienge=sienge, nome="TAGUAI - JARDIM DOS IPÊS III", status="Ativo")
    db.add(cc)
    plano = db.query(PaymentPlan).filter_by(nome="180x").first()
    if not plano:
        plano = PaymentPlan(nome="180x", condicoes_json=[])
        db.add(plano)
    db.commit()
    orc = Orcamento(
        descricao="Orçamento",
        ano=2027,
        tipo="VENDAS",
        status="Rascunho",
        departamento_id=dept.id,
        usuario_criador_id=1,
        versao_numero=1,
    )
    db.add(orc)
    db.flush()
    db.add(
        OrcamentoVendaItem(
            orcamento_id=orc.id,
            produto_id=cc.id,
            plano_venda_id=plano.id,
            mes=1,
            ano=2027,
            numero_vendas=2,
            ticket_medio=ticket,
            vgv=2 * ticket,
        )
    )
    db.commit()
    return orc, cc, plano


def test_le_so_2027_e_ignora_zero(tmp_path):
    path = tmp_path / "distratos.xlsx"
    _planilha(path, [("17701", "JARDIM DOS IPÊS III", {1: 2, 2: 0, 12: 2})])
    rows, err = ler_previsao_distratos_2027(str(path))
    assert err is None
    assert {(r["mes"], r["numero_vendas"], r["id_sienge"]) for r in rows} == {
        (1, 2, "17701"),
        (12, 2, "17701"),
    }


def test_grava_distrato_negativo_com_ticket_da_venda(db_session, tmp_path):
    orc, cc, plano = _rascunho_com_venda(db_session)
    path = tmp_path / "distratos.xlsx"
    _planilha(path, [("17701", "JARDIM DOS IPÊS III", {1: 2})])
    rel = importar_distratos_2027(db_session, usuario_id=1, gravar=True, path=str(path))
    assert rel["gravado"] is True
    assert rel["total_erros"] == 0
    assert rel["unidades"] == 2
    assert rel["vgv"] == -126000
    vendas = [
        i
        for i in db_session.query(OrcamentoVendaItem).filter_by(orcamento_id=orc.id).all()
        if (i.numero_vendas or 0) > 0
    ]
    dists = [
        i
        for i in db_session.query(OrcamentoVendaItem).filter_by(orcamento_id=orc.id).all()
        if (i.numero_vendas or 0) < 0
    ]
    assert len(vendas) == 1
    assert len(dists) == 1
    d = dists[0]
    assert d.produto_id == cc.id
    assert d.plano_venda_id == plano.id
    assert d.numero_vendas == -2
    assert d.ticket_medio == 63000
    assert d.vgv == -126000
    assert "Distrato" in d.observacao


def test_sem_ticket_de_venda_nao_grava(db_session, tmp_path):
    _rascunho_com_venda(db_session, sienge="12800", ticket=63000)
    path = tmp_path / "distratos.xlsx"
    _planilha(path, [("17701", "JARDIM DOS IPÊS III", {1: 2})])
    rel = importar_distratos_2027(db_session, usuario_id=1, gravar=True, path=str(path))
    assert rel["gravado"] is False
    assert any(e["codigo"] == "V02" for e in rel["erros"]) or any(
        e["codigo"] == "V06" for e in rel["erros"]
    )
    assert db_session.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.numero_vendas < 0).count() == 0
