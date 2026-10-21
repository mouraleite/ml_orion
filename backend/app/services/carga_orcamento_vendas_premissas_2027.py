"""Carga do orçamento de VENDAS 2027 a partir de PREMISSAS COMERCIAIS - v1.xlsx.

Lê abas de empreendimento com vendas mês a mês, ticket da aba e mix
A VISTA/24/36/48/60/120/180. Grava rascunho do departamento Vendas.
Não inventa centro de custo, plano nem ticket.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.payment_plan import PaymentPlan
from app.services.budget_shared import (
    DESCRICAO_DOCUMENTO_ORCAMENTO,
    STATUS_ORCAMENTO_BLOQUEADO,
)
from app.services.carga_orcamento_departamentos_2027 import _alinhar_sequencia_id
from app.services.excel_validator import _erro

ANO_CARGA = 2027
TIPO_CARGA = "VENDAS"
DEPT_VENDAS = "Vendas"
ABAS_APOIO = {"HOME", "LANÇAMENTOS", "LANCAMENTOS", "PLANOS", "PREÇOS COMERCIAIS", "PRECOS COMERCIAIS"}
MESES_COL = list(range(3, 15))  # C–N
MIX_LABELS = ("A VISTA", "24", "36", "48", "60", "120", "180")
PLANO_DEPARA = {
    "A VISTA": "À vista",
    "24": "24x",
    "36": "36x",
    "48": "48x",
    "60": "60x",
    "120": "120x",
    "180": "180x",
}
# C4 da aba → id_sienge (fechado com o Marcelo; 2026 + 15800/15900).
PRODUTO_PARA_SIENGE = {
    "reserva itapetininga": "15800",
    "fazenda cerrado": "15900",
    "novo horizonte (ita)": "16103",
    "reserva altavista i": "15300",
    "jardim dos ipes iii": "17701",
    "jardim dos ipes ii": "12800",
    "alto da bela vista": "13100",
    "novo horizonte (cc)": "13200",
    "livia": "13300",
    "livia ii": "13500",
    "central parque (avr)": "13700",
    "central parque ii (avr)": "13900",
    "reserva central parque ii (avr)": "14000",
    "reserva central parque (avr)": "13800",
    "parque cidade": "14100",
    "morada dos ipes ii": "14304",
    "reserva dos ipes": "14305",
    "cva - proprio": "14800",
    "reserva dos ramos - residencial": "14704",
    "jardim da serra iii": "12000",
    "reserva central parque (avr) - mldu": "17600",
    "mirante da serra": "17500",
}
PREMISSAS_XLSX_DEFAULT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "PREMISSAS COMERCIAIS - v1.xlsx"
    )
)


def _chave(texto: str) -> str:
    n = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(ch for ch in n if not unicodedata.combining(ch))
    return " ".join(sem_acento.strip().lower().split())


def _num(v) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _ano(v) -> Optional[int]:
    n = _num(v)
    if n is None:
        return None
    y = int(n)
    return y if 2000 <= y <= 2099 else None


def _ticket(m3, m4) -> Optional[float]:
    n3 = _num(m3)
    if n3 is not None and n3 != 0:
        return n3
    n4 = _num(m4)
    if n4 is not None and n4 != 0:
        return n4
    return None


def _copiar_se_preciso(path: str) -> Tuple[str, Optional[str]]:
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
    os.close(fd)
    shutil.copyfile(path, tmp)
    return tmp, tmp


def ler_premissas_comerciais(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Lê vendas 2027: um dict por célula de mix não-zero (produto, plano, mês)."""
    if not os.path.isfile(path):
        return [], f"Arquivo não encontrado: {path}"
    tmp = None
    try:
        aberto, tmp = _copiar_se_preciso(path)
        wb = load_workbook(aberto, data_only=True, read_only=True)
    except Exception as e:
        if tmp and os.path.isfile(tmp):
            os.remove(tmp)
        return [], f"Não foi possível abrir a planilha: {e}"

    out: List[Dict[str, Any]] = []
    try:
        for name in wb.sheetnames:
            if _chave(name) in {_chave(a) for a in ABAS_APOIO}:
                continue
            ws = wb[name]
            cells: Dict[int, List[Any]] = {}
            for i, row in enumerate(
                ws.iter_rows(min_row=1, max_row=45, max_col=16, values_only=True),
                start=1,
            ):
                cells[i] = list(row)
            r3 = cells.get(3) or []
            r4 = cells.get(4) or []
            cidade = r3[2] if len(r3) > 2 else None
            produto = r4[2] if len(r4) > 2 else None
            ticket = _ticket(
                r3[12] if len(r3) > 12 else None,
                r4[12] if len(r4) > 12 else None,
            )
            for start in (6, 15, 24, 33):
                prow = cells.get(start) or []
                if not prow:
                    continue
                rotulo = str(prow[1]).strip().upper() if len(prow) > 1 and prow[1] is not None else ""
                if rotulo != "PERIODO":
                    continue
                ano = _ano(prow[14] if len(prow) > 14 else None)
                if ano != ANO_CARGA:
                    continue
                for off in range(2, 9):
                    mrow = cells.get(start + off) or []
                    if len(mrow) < 3:
                        continue
                    lab = str(mrow[1]).strip() if mrow[1] is not None else ""
                    if lab not in MIX_LABELS:
                        continue
                    for mes_i, col in enumerate(range(2, 14), start=1):
                        qtd = _num(mrow[col] if len(mrow) > col else None) or 0.0
                        if qtd == 0:
                            continue
                        out.append(
                            {
                                "aba": name,
                                "cidade": cidade,
                                "produto_nome": produto,
                                "mix": lab,
                                "mes": mes_i,
                                "ano": ano,
                                "numero_vendas": qtd,
                                "ticket_medio": ticket,
                            }
                        )
    finally:
        wb.close()
        if tmp and os.path.isfile(tmp):
            os.remove(tmp)
    return out, None


def _validar(
    rows: List[Dict[str, Any]],
    ccs_por_sienge: Dict[str, CostCenter],
    planos_por_nome: Dict[str, PaymentPlan],
) -> Tuple[List[Dict], List[Dict]]:
    erros: List[Dict] = []
    agregados: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    origem: Dict[Tuple[int, int, int], int] = {}

    for i, row in enumerate(rows, start=1):
        linha_erros = False
        nome = str(row.get("produto_nome") or "").strip()
        mix = str(row.get("mix") or "").strip()
        sienge = PRODUTO_PARA_SIENGE.get(_chave(nome))
        if not nome:
            erros.append(_erro(i, "produto", "V01", f"Aba '{row.get('aba')}' sem nome de produto (C4)."))
            linha_erros = True
            cc = None
        elif not sienge:
            erros.append(
                _erro(
                    i,
                    "produto",
                    "V02",
                    f"Produto '{nome}' (aba {row.get('aba')}) não tem de-para de id_sienge.",
                )
            )
            linha_erros = True
            cc = None
        else:
            cc = ccs_por_sienge.get(str(sienge))
            if not cc:
                erros.append(
                    _erro(
                        i,
                        "produto",
                        "V02",
                        f"Centro de custo id_sienge '{sienge}' ({nome}) não encontrado.",
                    )
                )
                linha_erros = True

        plano_nome = PLANO_DEPARA.get(mix)
        if not plano_nome:
            erros.append(_erro(i, "plano_venda", "V03", f"Mix '{mix}' não mapeia para plano de venda."))
            linha_erros = True
            plano = None
        else:
            plano = planos_por_nome.get(_chave(plano_nome))
            if not plano:
                erros.append(
                    _erro(i, "plano_venda", "V03", f"Plano de Venda '{plano_nome}' não encontrado.")
                )
                linha_erros = True

        mes = row.get("mes")
        if not isinstance(mes, int) or not (1 <= mes <= 12):
            erros.append(_erro(i, "mes", "V05", f"Mês '{mes}' inválido."))
            linha_erros = True

        qtd_raw = row.get("numero_vendas")
        qtd_f = _num(qtd_raw)
        if qtd_f is None or qtd_f < 0 or abs(qtd_f - round(qtd_f)) > 1e-9:
            erros.append(_erro(i, "numero_vendas", "V06", f"Número de vendas inválido: '{qtd_raw}'."))
            linha_erros = True
            qtd = 0
        else:
            qtd = int(round(qtd_f))

        ticket = _num(row.get("ticket_medio"))
        if ticket is None or ticket <= 0:
            erros.append(
                _erro(
                    i,
                    "ticket_medio",
                    "V06",
                    f"Ticket médio ausente ou inválido em '{nome}' (aba {row.get('aba')}).",
                )
            )
            linha_erros = True
            ticket = 0.0

        if linha_erros or not cc or not plano or not isinstance(mes, int):
            continue

        chave = (cc.id, plano.id, mes)
        if chave not in agregados:
            agregados[chave] = {
                "produto_id": cc.id,
                "plano_venda_id": plano.id,
                "mes": mes,
                "ano": ANO_CARGA,
                "numero_vendas": 0,
                "ticket_medio": ticket,
                "vgv": 0.0,
                "id_sienge": cc.id_sienge,
                "produto_nome": cc.nome,
                "plano_nome": plano.nome,
            }
            origem[chave] = i
        elif abs(agregados[chave]["ticket_medio"] - ticket) > 0.009:
            erros.append(
                _erro(
                    i,
                    "ticket_medio",
                    "V06",
                    f"Ticket divergente para {nome} / {plano.nome} / mês {mes}.",
                )
            )
            continue
        agregados[chave]["numero_vendas"] += qtd
        agregados[chave]["vgv"] = agregados[chave]["numero_vendas"] * agregados[chave]["ticket_medio"]

    validas = list(agregados.values())
    return erros, validas


def _persistir(
    db: Session,
    dept: Departamento,
    linhas_validas: List[Dict],
    usuario_id: int,
    arquivo: str,
) -> int:
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
    if orc and orc.status in STATUS_ORCAMENTO_BLOQUEADO:
        raise PermissionError(
            "O orçamento deste departamento está em aprovação ou fechado. A importação foi recusada."
        )
    if not orc:
        orc = Orcamento(
            descricao=DESCRICAO_DOCUMENTO_ORCAMENTO,
            ano=ANO_CARGA,
            tipo=TIPO_CARGA,
            status="Rascunho",
            departamento_id=dept.id,
            usuario_criador_id=usuario_id,
            versao_numero=1,
        )
        db.add(orc)
        db.flush()

    grupo = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ANO_CARGA,
            Orcamento.tipo == TIPO_CARGA,
            Orcamento.departamento_id == dept.id,
            Orcamento.status != "Substituído",
            Orcamento.descricao == orc.descricao,
        )
        .all()
    )
    for doc in grupo:
        db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == doc.id).delete()
    _alinhar_sequencia_id(db, "orcamentos")
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
                f"{len(linhas_validas)} linhas importadas via Premissas Comerciais "
                f"2027 ({os.path.basename(arquivo)})"
            ),
            usuario_id=usuario_id,
        )
    )
    return orc.id


def importar_vendas_premissas_2027(
    db: Session,
    usuario_id: int,
    *,
    gravar: bool = False,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    arquivo = path or PREMISSAS_XLSX_DEFAULT
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
    relatorio["departamento_id"] = dept.id

    rows, err_aba = ler_premissas_comerciais(arquivo)
    if err_aba:
        relatorio["mensagem"] = err_aba
        relatorio["total_erros"] = 1
        return relatorio
    relatorio["total_linhas"] = len(rows)

    ccs = {
        str(c.id_sienge).strip(): c
        for c in db.query(CostCenter).all()
        if c.id_sienge
    }
    planos = { _chave(p.nome): p for p in db.query(PaymentPlan).all() if p.nome }

    erros, validas = _validar(rows, ccs, planos)
    relatorio["total_erros"] = len(erros)
    relatorio["total_validas"] = len(validas)
    relatorio["erros"] = erros[:50]
    relatorio["unidades"] = sum(int(v["numero_vendas"]) for v in validas)
    relatorio["vgv"] = sum(float(v["vgv"]) for v in validas)
    if erros:
        relatorio["mensagem"] = (
            "Importação recusada: a planilha contém erros. Nenhum dado foi alterado."
        )
        return relatorio
    if not validas:
        relatorio["mensagem"] = "Nenhuma venda 2027 com valor para gravar."
        return relatorio

    if not gravar:
        relatorio["mensagem"] = (
            f"{len(validas)} linha(s) válidas no rascunho de Vendas 2027 (simulação)."
        )
        return relatorio

    try:
        oid = _persistir(db, dept, validas, usuario_id, arquivo)
        db.commit()
        relatorio["gravado"] = True
        relatorio["orcamento_id"] = oid
        relatorio["mensagem"] = (
            f"{len(validas)} linha(s) gravadas no rascunho de Vendas 2027."
        )
    except PermissionError as e:
        db.rollback()
        relatorio["mensagem"] = str(e)
        relatorio["total_erros"] = 1
    except Exception as e:
        db.rollback()
        relatorio["mensagem"] = f"Falha ao gravar: {e}"
        relatorio["total_erros"] = 1
    return relatorio


def remap_sienge_rascunho_vendas(
    db: Session,
    usuario_id: int,
    *,
    origem: str = "15600",
    destino: str = "17701",
    gravar: bool = False,
) -> Dict[str, Any]:
    """Troca o centro de custo das linhas de venda do rascunho 2027. Não mexe em ticket nem quantidade."""
    relatorio: Dict[str, Any] = {
        "ano": ANO_CARGA,
        "tipo": TIPO_CARGA,
        "origem": origem,
        "destino": destino,
        "gravado": False,
        "itens": 0,
        "unidades": 0,
        "mensagem": None,
        "erros": [],
        "total_erros": 0,
    }
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
            "O orçamento deste departamento está em aprovação ou fechado. A correção foi recusada."
        )
        relatorio["total_erros"] = 1
        return relatorio
    cc_origem = db.query(CostCenter).filter(CostCenter.id_sienge == origem).first()
    cc_destino = db.query(CostCenter).filter(CostCenter.id_sienge == destino).first()
    if not cc_origem:
        relatorio["mensagem"] = f"Centro de custo '{origem}' não encontrado."
        relatorio["total_erros"] = 1
        return relatorio
    if not cc_destino:
        relatorio["mensagem"] = f"Centro de custo '{destino}' não encontrado."
        relatorio["total_erros"] = 1
        return relatorio
    itens = (
        db.query(OrcamentoVendaItem)
        .filter(
            OrcamentoVendaItem.orcamento_id == orc.id,
            OrcamentoVendaItem.produto_id == cc_origem.id,
        )
        .all()
    )
    relatorio["orcamento_id"] = orc.id
    relatorio["itens"] = len(itens)
    relatorio["unidades"] = sum(int(i.numero_vendas or 0) for i in itens)
    if not itens:
        relatorio["mensagem"] = f"Nenhuma linha de venda no {origem} para mover."
        return relatorio
    for item in itens:
        item.produto_id = cc_destino.id
    db.flush()
    if not gravar:
        relatorio["mensagem"] = (
            f"{len(itens)} linha(s) do {origem} prontas para ir ao {destino} (simulação)."
        )
        return relatorio
    try:
        db.add(
            Auditoria(
                evento="Alteracao",
                tabela_afetada="orcamento_venda_itens",
                registro_id=orc.id,
                campo="produto_id",
                valor_anterior=origem,
                novo_valor=destino,
                usuario_id=usuario_id,
            )
        )
        db.commit()
        relatorio["gravado"] = True
        relatorio["mensagem"] = (
            f"{len(itens)} linha(s) movidas de {origem} para {destino}."
        )
    except Exception as e:
        db.rollback()
        relatorio["mensagem"] = f"Falha ao gravar: {e}"
        relatorio["total_erros"] = 1
    return relatorio
