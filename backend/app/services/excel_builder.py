"""
excel_builder.py — Gera planilhas Excel: modelos em branco e exportação de orçamentos.
Utiliza openpyxl com estilos e dropdowns para facilitar o preenchimento.
"""
import io
from typing import Optional
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.orm import Session

from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.services.periodos import MESES_STR

MESES      = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ── Estilos ──────────────────────────────────────────────────────────────────

def _header_style() -> dict:
    return dict(
        font=Font(bold=True, color="FFFFFF", size=11),
        fill=PatternFill("solid", fgColor="1A3A5C"),
        alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
        border=Border(
            bottom=Side(style="thin", color="AAAAAA"),
            right=Side(style="thin", color="AAAAAA"),
        ),
    )

def _apply_style(cell, style: dict):
    for attr, val in style.items():
        setattr(cell, attr, val)

def _apply_header(ws, row: int, cols: list):
    hs = _header_style()
    for col_idx, label in enumerate(cols, start=1):
        cell = ws.cell(row=row, column=col_idx, value=label)
        _apply_style(cell, hs)
    ws.row_dimensions[row].height = 30

def _zebra_fill(row_idx: int) -> Optional[PatternFill]:
    if row_idx % 2 == 0:
        return PatternFill("solid", fgColor="F0F4FA")
    return None

def _add_lookup_sheet(wb: Workbook, sheet_name: str, values: list) -> str:
    """Adiciona aba oculta com lista de valores para dropdown."""
    ws_lookup = wb.create_sheet(sheet_name)
    ws_lookup.sheet_state = "hidden"
    for i, v in enumerate(values, start=1):
        ws_lookup.cell(row=i, column=1, value=v)
    last_row = len(values) or 1
    return f"'{sheet_name}'!$A$1:$A${last_row}"


# ── Modelo em Branco — Despesas / Receitas ───────────────────────────────────

def gerar_modelo_despesas_receitas(
    db: Session,
    tipo: str,
    ano: int,
    departamento_id: Optional[int] = None,
) -> bytes:
    """Gera template .xlsx em branco para importação de Despesas ou Receitas."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"Orçamento_{tipo}_{ano}"

    produtos = db.query(CostCenter).order_by(CostCenter.nome).all()
    planos   = db.query(FinancialPlan).order_by(FinancialPlan.name).all()

    nomes_produtos = [p.nome for p in produtos]
    nomes_planos   = [p.name for p in planos]

    ref_prod  = _add_lookup_sheet(wb, "Produtos",  nomes_produtos)
    ref_plano = _add_lookup_sheet(wb, "Planos",    nomes_planos)

    # Cabeçalho
    header = ["produto", "plano_financeiro"] + MESES_STR + ["observacao"]
    _apply_header(ws, 1, header)

    # Larguras
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 28
    for col in range(3, 15):
        ws.column_dimensions[get_column_letter(col)].width = 11
    ws.column_dimensions[get_column_letter(15)].width = 35

    # Linhas de exemplo (50 linhas editáveis)
    num_data_rows = 50
    for r in range(2, 2 + num_data_rows):
        fill = _zebra_fill(r)
        for c in range(1, len(header) + 1):
            cell = ws.cell(row=r, column=c, value=None)
            if fill:
                cell.fill = fill
            if c >= 3 and c <= 14:
                cell.number_format = '#,##0.00'
            cell.alignment = Alignment(vertical="center")

    # Dropdowns — criados UMA VEZ fora do loop
    dv_prod = DataValidation(type="list", formula1=ref_prod, allow_blank=True,
                              error="Produto não encontrado.", errorTitle="Inválido", showErrorMessage=True)
    dv_plan = DataValidation(type="list", formula1=ref_plano, allow_blank=True,
                              error="Plano não encontrado.", errorTitle="Inválido", showErrorMessage=True)
    dv_prod.sqref = f"A2:A{1 + num_data_rows}"
    dv_plan.sqref = f"B2:B{1 + num_data_rows}"
    ws.add_data_validation(dv_prod)
    ws.add_data_validation(dv_plan)

    # Linha de instrução
    ws.insert_rows(1)
    instr = ws.cell(row=1, column=1,
        value=f"MODELO DE IMPORTAÇÃO — {tipo} — {ano} | Não altere o cabeçalho. Gerado em {datetime.now():%d/%m/%Y %H:%M}")
    instr.font = Font(bold=True, color="1A3A5C", italic=True)
    ws.merge_cells(f"A1:{get_column_letter(len(header))}1")
    ws.row_dimensions[1].height = 20

    # Congelar painel
    ws.freeze_panes = "C3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Modelo em Branco — Vendas ────────────────────────────────────────────────

def gerar_modelo_vendas(db: Session, ano: int) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"Orçamento_VENDAS_{ano}"

    produtos    = db.query(CostCenter).order_by(CostCenter.nome).all()
    planos_vnd  = db.query(PaymentPlan).order_by(PaymentPlan.name).all()

    ref_prod  = _add_lookup_sheet(wb, "Produtos",    [p.nome for p in produtos])
    ref_plano = _add_lookup_sheet(wb, "PlanosVenda", [p.name for p in planos_vnd])

    header = ["produto", "plano_venda", "mes", "numero_vendas", "ticket_medio", "vgv"]
    _apply_header(ws, 1, header)

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16

    num_data_rows = 50
    for r in range(2, 2 + num_data_rows):
        fill = _zebra_fill(r)
        for c in range(1, 7):
            cell = ws.cell(row=r, column=c)
            if fill:
                cell.fill = fill
            if c in (4, 5, 6):
                cell.number_format = '#,##0.00'
            cell.alignment = Alignment(vertical="center")

    dv_prod = DataValidation(type="list", formula1=ref_prod, allow_blank=True,
                              showErrorMessage=True, error="Produto inválido.")
    dv_plan = DataValidation(type="list", formula1=ref_plano, allow_blank=True,
                              showErrorMessage=True, error="Plano inválido.")
    dv_mes  = DataValidation(type="whole", operator="between", formula1="1", formula2="12",
                              showErrorMessage=True, error="Mês deve ser de 1 a 12.")
    ws.add_data_validation(dv_prod)
    ws.add_data_validation(dv_plan)
    ws.add_data_validation(dv_mes)
    dv_prod.sqref = f"A2:A{1 + num_data_rows}"
    dv_plan.sqref = f"B2:B{1 + num_data_rows}"
    dv_mes.sqref  = f"C2:C{1 + num_data_rows}"

    ws.insert_rows(1)
    instr = ws.cell(row=1, column=1,
        value=f"MODELO DE IMPORTAÇÃO — VENDAS — {ano} | Gerado em {datetime.now():%d/%m/%Y %H:%M}")
    instr.font = Font(bold=True, color="1A3A5C", italic=True)
    ws.merge_cells("A1:F1")
    ws.freeze_panes = "A3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Exportar Orçamento Preenchido ────────────────────────────────────────────

def exportar_orcamento(orcamento_id: int, db: Session) -> bytes:
    """Exporta um orçamento existente para Excel (somente leitura)."""
    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orc:
        raise ValueError(f"Orçamento {orcamento_id} não encontrado.")

    wb = Workbook()
    ws = wb.active
    ws.title = f"Orçamento_{orc.tipo}_{orc.ano}_v{orc.versao_numero}"

    hs = _header_style()

    if orc.tipo == "VENDAS":
        header = ["Produto", "Plano de Venda", "Mês", "Nº Vendas", "Ticket Médio (R$)", "VGV (R$)"]
        _apply_header(ws, 1, header)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 8
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 16

        for r, item in enumerate(orc.itens_venda, start=2):
            prod  = db.query(CostCenter).filter(CostCenter.id == item.produto_id).first()
            plano = db.query(PaymentPlan).filter(PaymentPlan.id == item.plano_venda_id).first()
            fill  = _zebra_fill(r)
            vals  = [
                prod.nome  if prod  else item.produto_id,
                plano.name if plano else item.plano_venda_id,
                item.mes,
                item.numero_vendas or 0,
                item.ticket_medio  or 0.0,
                item.vgv           or 0.0,
            ]
            for c, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=c, value=v)
                if fill:
                    cell.fill = fill
                if c in (5, 6):
                    cell.number_format = '#,##0.00'
    else:
        header = ["Produto", "Plano Financeiro"] + MESES + ["Total Anual (R$)", "Observação"]
        _apply_header(ws, 1, header)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 28
        for c in range(3, 15):
            ws.column_dimensions[get_column_letter(c)].width = 11
        ws.column_dimensions[get_column_letter(15)].width = 16
        ws.column_dimensions[get_column_letter(16)].width = 35

        for r, item in enumerate(orc.itens_despesa, start=2):
            prod  = db.query(CostCenter).filter(CostCenter.id == item.produto_id).first()
            plano = db.query(FinancialPlan).filter(FinancialPlan.id == item.plano_financeiro_id).first()
            fill  = _zebra_fill(r)
            meses_vals = [getattr(item, m) or 0.0 for m in MESES_STR]
            total = sum(meses_vals)
            vals = [
                prod.nome  if prod  else item.produto_id,
                plano.name if plano else item.plano_financeiro_id,
                *meses_vals,
                total,
                item.observacao or "",
            ]
            for c, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=c, value=v)
                if fill:
                    cell.fill = fill
                if 3 <= c <= 16:
                    cell.number_format = '#,##0.00'

    # Meta na última linha
    ws.freeze_panes = "C2"

    # Aba de metadados
    ws_meta = wb.create_sheet("Metadados")
    for r, (k, v) in enumerate([
        ("Orçamento ID",   orc.id),
        ("Tipo",           orc.tipo),
        ("Ano",            orc.ano),
        ("Status",         orc.status),
        ("Versão",         orc.versao_numero),
        ("Exportado em",   datetime.now().strftime("%d/%m/%Y %H:%M")),
    ], start=1):
        ws_meta.cell(row=r, column=1, value=k).font = Font(bold=True)
        ws_meta.cell(row=r, column=2, value=str(v))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def exportar_forecast(forecast_id: int, db: Session) -> bytes:
    """Exporta um forecast existente para Excel (somente leitura)."""
    orc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not orc:
        raise ValueError(f"Forecast {forecast_id} não encontrado.")

    wb = Workbook()
    ws = wb.active
    ws.title = f"Forecast_{orc.tipo}_{orc.ano}_v{orc.versao_numero}"

    hs = _header_style()

    if orc.tipo == "VENDAS":
        header = ["Produto", "Plano de Venda", "Mês", "Nº Vendas", "Ticket Médio (R$)", "VGV (R$)"]
        _apply_header(ws, 1, header)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 8
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 16

        for r, item in enumerate(orc.itens_venda, start=2):
            prod  = db.query(CostCenter).filter(CostCenter.id == item.produto_id).first()
            plano = db.query(PaymentPlan).filter(PaymentPlan.id == item.plano_venda_id).first()
            fill  = _zebra_fill(r)
            vals  = [
                prod.nome  if prod  else item.produto_id,
                plano.name if plano else item.plano_venda_id,
                item.mes,
                item.numero_vendas,
                item.ticket_medio,
                item.vgv
            ]
            for c_idx, val in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=c_idx, value=val)
                if fill: cell.fill = fill
                if c_idx in (4, 5, 6):
                    cell.number_format = '#,##0.00'

    else:
        header = ["Produto", "Plano Financeiro"] + MESES_STR + ["Observacao"]
        _apply_header(ws, 1, header)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 28
        for col in range(3, 15):
            ws.column_dimensions[get_column_letter(col)].width = 12
        ws.column_dimensions["O"].width = 30

        for r, item in enumerate(orc.itens, start=2):
            prod  = db.query(CostCenter).filter(CostCenter.id == item.produto_id).first()
            plano = db.query(FinancialPlan).filter(FinancialPlan.id == item.plano_financeiro_id).first()
            fill  = _zebra_fill(r)
            vals = [
                prod.nome  if prod  else item.produto_id,
                plano.name if plano else item.plano_financeiro_id,
                item.jan, item.fev, item.mar, item.abr, item.mai, item.jun,
                item.jul, item.ago, item.set, item.out, item.nov, item.dez,
                item.observacao
            ]
            for c_idx, val in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=c_idx, value=val)
                if fill: cell.fill = fill
                if 3 <= c_idx <= 14:
                    cell.number_format = '#,##0.00'

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
