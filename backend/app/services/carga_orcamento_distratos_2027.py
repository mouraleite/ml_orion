"""Carga de distratos 2027 a partir de Previsão distratos 4T26 e 2027.xlsx.

Lê PREVISÕES DE CANCELAMENTOS (jan–dez/2027). Ticket vem da venda já
gravada no rascunho. Não inventa produto nem preço.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.payment_plan import PaymentPlan
from app.services.budget_shared import (
    STATUS_ORCAMENTO_BLOQUEADO,
    is_venda_distrato,
)
from app.services.carga_orcamento_departamentos_2027 import _alinhar_sequencia_id
from app.services.carga_orcamento_vendas_premissas_2027 import ANO_CARGA, DEPT_VENDAS, TIPO_CARGA
from app.services.excel_validator import _erro, _to_int

ABA = "TABELA DINAMICA"
COL_EMP = 2  # B
COL_JAN_2027 = 46  # AT
COL_DEZ_2027 = 57  # BE
PLANO_DISTRATO = "180x"
OBS_DISTRATO = "(Distrato)"
DISTRATOS_XLSX_DEFAULT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "Previsão distratos 4T26 e 2027.xlsx",
    )
)


def _copiar(path: str) -> str:
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
    os.close(fd)
    shutil.copyfile(path, tmp)
    return tmp


def _sienge(rotulo: str) -> Optional[str]:
    if not rotulo:
        return None
    token = str(rotulo).split(" - ", 1)[0].strip()
    return token if token.isdigit() else None


def ler_previsao_distratos_2027(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not os.path.isfile(path):
        return [], f"Arquivo não encontrado: {path}"
    tmp = None
    try:
        tmp = _copiar(path)
        wb = load_workbook(tmp, data_only=True, read_only=True)
    except Exception as e:
        if tmp and os.path.isfile(tmp):
            os.remove(tmp)
        return [], f"Não foi possível abrir a planilha: {e}"

    out: List[Dict[str, Any]] = []
    try:
        if ABA not in wb.sheetnames:
            return [], f"Aba '{ABA}' não encontrada."
        ws = wb[ABA]
        for i, row in enumerate(
            ws.iter_rows(min_row=8, max_row=40, max_col=COL_DEZ_2027, values_only=True),
            start=8,
        ):
            rotulo = row[COL_EMP - 1] if len(row) >= COL_EMP else None
            if rotulo is None:
                continue
            if str(rotulo).strip().lower().startswith("total"):
                continue
            sienge = _sienge(str(rotulo))
            if not sienge:
                continue
            for mes, col in enumerate(range(COL_JAN_2027, COL_DEZ_2027 + 1), start=1):
                raw = row[col - 1] if len(row) >= col else None
                qtd = _to_int(raw) if raw not in (None, "") else 0
                if not qtd:
                    continue
                out.append(
                    {
                        "linha": i,
                        "id_sienge": sienge,
                        "rotulo": str(rotulo).strip(),
                        "mes": mes,
                        "numero_vendas": qtd,
                    }
                )
    finally:
        wb.close()
        if tmp and os.path.isfile(tmp):
            os.remove(tmp)
    return out, None


def _ticket_por_produto(db: Session, orcamento_id: int) -> Dict[int, float]:
    tickets: Dict[int, float] = {}
    itens = (
        db.query(OrcamentoVendaItem)
        .filter(OrcamentoVendaItem.orcamento_id == orcamento_id)
        .all()
    )
    for item in itens:
        if is_venda_distrato(item):
            continue
        tk = float(item.ticket_medio or 0.0)
        if tk <= 0:
            continue
        atual = tickets.get(item.produto_id)
        if atual is None:
            tickets[item.produto_id] = tk
    return tickets


def _validar(
    rows: List[Dict[str, Any]],
    ccs: Dict[str, CostCenter],
    tickets: Dict[int, float],
    plano: PaymentPlan,
) -> Tuple[List[Dict], List[Dict]]:
    erros: List[Dict] = []
    validas: List[Dict] = []
    for row in rows:
        i = int(row["linha"])
        sienge = row["id_sienge"]
        cc = ccs.get(sienge)
        if not cc:
            erros.append(
                _erro(i, "produto", "V02", f"Centro de custo '{sienge}' não encontrado.")
            )
            continue
        ticket = tickets.get(cc.id)
        if ticket is None or ticket <= 0:
            erros.append(
                _erro(
                    i,
                    "ticket_medio",
                    "V06",
                    f"Produto {sienge} sem ticket de venda 2027 no rascunho.",
                )
            )
            continue
        qtd = int(row["numero_vendas"])
        validas.append(
            {
                "produto_id": cc.id,
                "plano_venda_id": plano.id,
                "mes": row["mes"],
                "ano": ANO_CARGA,
                "numero_vendas": -qtd,
                "ticket_medio": ticket,
                "vgv": -qtd * ticket,
                "observacao": OBS_DISTRATO,
                "id_sienge": sienge,
            }
        )
    return erros, validas


def _persistir(
    db: Session,
    orc: Orcamento,
    linhas_validas: List[Dict],
    usuario_id: int,
    arquivo: str,
) -> int:
    atuais = (
        db.query(OrcamentoVendaItem)
        .filter(OrcamentoVendaItem.orcamento_id == orc.id)
        .all()
    )
    for item in atuais:
        if is_venda_distrato(item):
            db.delete(item)
    _alinhar_sequencia_id(db, "orcamento_venda_itens")
    _alinhar_sequencia_id(db, "auditoria")
    for linha in linhas_validas:
        db.add(
            OrcamentoVendaItem(
                orcamento_id=orc.id,
                produto_id=linha["produto_id"],
                plano_venda_id=linha["plano_venda_id"],
                mes=linha["mes"],
                ano=linha["ano"],
                numero_vendas=linha["numero_vendas"],
                ticket_medio=linha["ticket_medio"],
                vgv=linha["vgv"],
                observacao=linha["observacao"],
            )
        )
    db.add(
        Auditoria(
            evento="Importacao",
            tabela_afetada="orcamentos",
            registro_id=orc.id,
            campo=None,
            valor_anterior=None,
            novo_valor=(
                f"{len(linhas_validas)} linhas de distrato 2027 "
                f"({os.path.basename(arquivo)})"
            ),
            usuario_id=usuario_id,
        )
    )
    return orc.id


def importar_distratos_2027(
    db: Session,
    usuario_id: int,
    *,
    gravar: bool = False,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    arquivo = path or DISTRATOS_XLSX_DEFAULT
    relatorio: Dict[str, Any] = {
        "ano": ANO_CARGA,
        "tipo": TIPO_CARGA,
        "departamento": DEPT_VENDAS,
        "arquivo": arquivo,
        "gravado": False,
        "orcamento_id": None,
        "total_linhas": 0,
        "total_validas": 0,
        "total_erros": 0,
        "unidades": 0,
        "vgv": 0.0,
        "erros": [],
        "mensagem": None,
    }
    if not os.path.isfile(arquivo):
        relatorio["mensagem"] = f"Arquivo não encontrado: {arquivo}"
        relatorio["total_erros"] = 1
        return relatorio

    dept = db.query(Departamento).filter(Departamento.nome == DEPT_VENDAS).first()
    if not dept:
        relatorio["mensagem"] = f"Departamento '{DEPT_VENDAS}' não encontrado no cadastro."
        relatorio["total_erros"] = 1
        return relatorio
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ANO_CARGA,
            Orcamento.tipo == TIPO_CARGA,
            Orcamento.departamento_id == dept.id,
            Orcamento.status != "Substituído",
        )
        .order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc())
        .first()
    )
    if not orc:
        relatorio["mensagem"] = "Rascunho de Vendas 2027 não encontrado."
        relatorio["total_erros"] = 1
        return relatorio
    if orc.status in STATUS_ORCAMENTO_BLOQUEADO:
        relatorio["mensagem"] = (
            "O orçamento deste departamento está em aprovação ou fechado. A importação foi recusada."
        )
        relatorio["total_erros"] = 1
        return relatorio
    relatorio["orcamento_id"] = orc.id
    relatorio["departamento_id"] = dept.id

    plano = db.query(PaymentPlan).filter(PaymentPlan.nome == PLANO_DISTRATO).first()
    if not plano:
        relatorio["mensagem"] = f"Plano de Venda '{PLANO_DISTRATO}' não encontrado."
        relatorio["total_erros"] = 1
        return relatorio

    rows, err_aba = ler_previsao_distratos_2027(arquivo)
    if err_aba:
        relatorio["mensagem"] = err_aba
        relatorio["total_erros"] = 1
        return relatorio
    relatorio["total_linhas"] = len(rows)

    ccs = {str(c.id_sienge).strip(): c for c in db.query(CostCenter).all() if c.id_sienge}
    tickets = _ticket_por_produto(db, orc.id)
    erros, validas = _validar(rows, ccs, tickets, plano)
    relatorio["total_erros"] = len(erros)
    relatorio["total_validas"] = len(validas)
    relatorio["erros"] = erros[:50]
    relatorio["unidades"] = -sum(int(v["numero_vendas"]) for v in validas)
    relatorio["vgv"] = sum(float(v["vgv"]) for v in validas)
    if erros:
        relatorio["mensagem"] = (
            "Importação recusada: a planilha contém erros. Nenhum dado foi alterado."
        )
        return relatorio
    if not validas:
        relatorio["mensagem"] = "Nenhum distrato 2027 com valor para gravar."
        return relatorio
    if not gravar:
        relatorio["mensagem"] = (
            f"{len(validas)} linha(s) de distrato válidas no rascunho de Vendas 2027 (simulação)."
        )
        return relatorio
    try:
        oid = _persistir(db, orc, validas, usuario_id, arquivo)
        db.commit()
        relatorio["gravado"] = True
        relatorio["orcamento_id"] = oid
        relatorio["mensagem"] = (
            f"{len(validas)} linha(s) de distrato gravadas no rascunho de Vendas 2027."
        )
    except Exception as e:
        db.rollback()
        relatorio["mensagem"] = f"Falha ao gravar: {e}"
        relatorio["total_erros"] = 1
    return relatorio
