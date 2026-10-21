"""Carga de Orçamento Despesas 2027 a partir das planilhas de Elaboração do Orçamento.

Lê a aba fImportacao de cada departamento e grava o documento daquele
departamento — o mesmo formato do importador Excel da tela.
Não inventa centro de custo nem plano: código/nome ausentes viram erro.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unicodedata
import zipfile
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.cost_center import CostCenter
from app.models.departamento import Departamento, DepartamentoPlano
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.budget_shared import (
    DESCRICAO_DOCUMENTO_ORCAMENTO,
    STATUS_ORCAMENTO_BLOQUEADO,
)
from app.services.excel_validator import _erro, _to_float
from app.services.periodos import MESES_STR

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

SHAREPOINT_ORCAMENTO_DIR = (
    r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA"
    r"\Banco de Dados - Documentos\Elaboração do Orçamento"
)
ANO_CARGA = 2027
TIPO_CARGA = "DESPESAS"
ABA_IMPORTACAO = "fimportacao"
ABA_DESPESAS_XLSX = "despesas"
DEPT_CONTROLADORIA = "Controladoria"
DESPESAS_XLSX_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Despesas.xlsx")
)

# Pasta da Elaboração → nome do departamento no Apoio (fechado com o Marcelo).
PASTA_PARA_DEPARTAMENTO = {
    "conselho": "Conselho",
    "controladoria": "Controladoria",
    "engenharia": "Engenharia",
    "marketing": "Marketing",
    "novos negocios": "Novos Negócios",
    "pagadoria": "Tesouraria",
    "pessoas": "Pessoas",
    "projetos": "Projetos planejamento",
    "relacionamento": "Atendimento ao Cliente",
    "servicos": "Serviços",
    "vendas": "Vendas",
}
PASTAS_IGNORADAS = {"materiais", "modelos", "contratos", "sdr"}


def _chave(texto: str) -> str:
    n = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(ch for ch in n if not unicodedata.combining(ch))
    return " ".join(sem_acento.strip().lower().split())


def _tem_importacao_no_nome(arquivo: str) -> bool:
    return "importacao" in _chave(arquivo)


def _col_row(cell_ref: str) -> Tuple[int, int]:
    col = "".join(ch for ch in cell_ref if ch.isalpha())
    row = int("".join(ch for ch in cell_ref if ch.isdigit()) or 0)
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n, row


def _shared_strings(z: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out: List[str] = []
    for si in root.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return out


def _cell_value(c, sst: List[str]):
    t = c.attrib.get("t")
    v = c.find("m:v", NS)
    if t == "s" and v is not None and v.text is not None:
        idx = int(v.text)
        return sst[idx] if 0 <= idx < len(sst) else v.text
    if t == "inlineStr":
        return "".join(t.text or "" for t in c.findall(".//m:t", NS))
    if v is not None:
        return v.text
    return None


def _list_sheets(z: zipfile.ZipFile) -> List[Dict[str, str]]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pr:Relationship", NS)
    }
    sheets = []
    for sh in wb.find("m:sheets", NS).findall("m:sheet", NS):
        rid = sh.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        target = rid_to_target.get(rid, "")
        if target.startswith("/"):
            xml_path = target.lstrip("/")
        elif target.startswith("xl/"):
            xml_path = target
        else:
            xml_path = "xl/" + target.lstrip("/")
        sheets.append({"name": sh.attrib.get("name") or "", "xml": xml_path})
    return sheets


def _norm_header(valor) -> str:
    return (
        str(valor or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("á", "a")
        .replace("ã", "a")
        .replace("í", "i")
    )


def _norm_sienge(valor) -> str:
    if valor is None:
        return ""
    s = str(valor).strip()
    if not s:
        return ""
    try:
        f = float(s.replace(",", "."))
        if f == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s


def ler_aba_fimportacao(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Lê a aba fImportacao. Retorna (linhas, erro). Não usa a aba ativa."""
    tmp_copy = None
    rows: Dict[int, Dict[int, Any]] = {}
    try:
        fd, tmp_copy = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
        os.close(fd)
        shutil.copyfile(path, tmp_copy)
        with zipfile.ZipFile(tmp_copy) as z:
            sst = _shared_strings(z)
            target = None
            for s in _list_sheets(z):
                if _chave(s["name"]).replace(" ", "") == ABA_IMPORTACAO:
                    target = s
                    break
            if target is None:
                return [], "Aba fImportacao não encontrada."
            if target["xml"] not in z.namelist():
                return [], f"XML da aba fImportacao ausente ({target['xml']})."
            root = ET.fromstring(z.read(target["xml"]))
            sheet_data = root.find("m:sheetData", NS)
            rows: Dict[int, Dict[int, Any]] = {}
            for row in sheet_data.findall("m:row", NS):
                ridx = int(row.attrib.get("r", "0"))
                cells: Dict[int, Any] = {}
                for c in row.findall("m:c", NS):
                    col, _ = _col_row(c.attrib.get("r", ""))
                    cells[col] = _cell_value(c, sst)
                if cells:
                    rows[ridx] = cells
    except Exception as e:
        return [], f"Não foi possível abrir o arquivo: {e}"
    finally:
        if tmp_copy:
            try:
                os.remove(tmp_copy)
            except OSError:
                pass

    if 1 not in rows:
        return [], "Aba fImportacao sem cabeçalho."

    header_row = rows[1]
    hmap = {_norm_header(header_row.get(i)): i for i in header_row}
    idx_emp = hmap.get("empreendimento")
    idx_plano = hmap.get("plano_financeiro")
    idx_meses = [hmap.get(m) for m in MESES_STR]
    if not idx_emp or not idx_plano:
        return [], "Aba fImportacao sem colunas Empreendimento e/ou Plano Financeiro."
    if any(ix is None for ix in idx_meses):
        return [], "Aba fImportacao sem as 12 colunas de mês (Jan–Dez)."

    out: List[Dict[str, Any]] = []
    for ridx in sorted(k for k in rows if k > 1):
        cells = rows[ridx]
        emp = _norm_sienge(cells.get(idx_emp))
        plano = str(cells.get(idx_plano) or "").strip()
        meses = {}
        for mes, ix in zip(MESES_STR, idx_meses):
            raw = cells.get(ix)
            if raw is None or str(raw).strip() == "":
                meses[mes] = 0.0
            else:
                v = _to_float(raw)
                meses[mes] = v
        if not emp and not plano and not any(meses.values()):
            continue
        out.append({"linha": ridx, "empreendimento": emp, "plano_financeiro": plano, **meses})
    return out, None


def _achar_arquivos(base_dir: str) -> List[Dict[str, str]]:
    encontrados: List[Dict[str, str]] = []
    if not os.path.isdir(base_dir):
        return encontrados
    for pasta in sorted(os.listdir(base_dir)):
        pasta_path = os.path.join(base_dir, pasta)
        if not os.path.isdir(pasta_path):
            continue
        chave = _chave(pasta)
        ano_path = os.path.join(pasta_path, str(ANO_CARGA))
        if not os.path.isdir(ano_path):
            continue
        for fn in os.listdir(ano_path):
            if fn.startswith("~$"):
                continue
            if not fn.lower().endswith((".xlsx", ".xlsm")):
                continue
            if not _tem_importacao_no_nome(fn):
                continue
            encontrados.append(
                {
                    "pasta": pasta,
                    "chave": chave,
                    "arquivo": fn,
                    "path": os.path.join(ano_path, fn),
                }
            )
    return encontrados


def _indexar_cadastro(db: Session):
    ccs = {
        str(c.id_sienge).strip(): c
        for c in db.query(CostCenter).all()
        if c.id_sienge and str(c.id_sienge).strip()
    }
    planos = {
        p.name.strip().lower(): p
        for p in db.query(FinancialPlan).all()
        if p.name
    }
    depts = {d.nome.strip().lower(): d for d in db.query(Departamento).all() if d.nome}
    # Catálogo da tela (planos_ids_leitura): plano liberado no departamento.
    # produto_plano_financeiro está vazio em produção; exigir isso bloquearia 100% das linhas.
    dept_planos = {
        (r.departamento_id, r.plano_financeiro_id)
        for r in db.query(DepartamentoPlano).filter(DepartamentoPlano.permitido.is_(True)).all()
    }
    return ccs, planos, depts, dept_planos


def _validar_linhas(
    rows: List[Dict[str, Any]],
    departamento_id: int,
    ccs: Dict[str, CostCenter],
    planos: Dict[str, FinancialPlan],
    dept_planos: set,
) -> Tuple[List[Dict], List[Dict]]:
    erros: List[Dict] = []
    agregados: Dict[Tuple[int, int], Dict[str, Any]] = {}
    origem_linha: Dict[Tuple[int, int], int] = {}

    for row in rows:
        linha = int(row["linha"])
        emp = row.get("empreendimento") or ""
        plano_raw = row.get("plano_financeiro") or ""
        linha_erros = False

        valores = {}
        mes_invalido = False
        for mes in MESES_STR:
            v = row.get(mes)
            if v is None:
                erros.append(_erro(linha, mes, "V06", f"Valor inválido na coluna '{mes}'."))
                mes_invalido = True
            else:
                valores[mes] = float(v)
        if mes_invalido:
            continue
        if not any(valores.values()):
            continue

        if not emp:
            erros.append(_erro(linha, "empreendimento", "V01", "Campo obrigatório 'Empreendimento' está vazio."))
            linha_erros = True
        if not plano_raw:
            erros.append(_erro(linha, "plano_financeiro", "V01", "Campo obrigatório 'plano_financeiro' está vazio."))
            linha_erros = True

        cc = ccs.get(emp) if emp else None
        if emp and not cc:
            erros.append(
                _erro(
                    linha,
                    "empreendimento",
                    "V02",
                    f"Centro de custo id_sienge '{emp}' não encontrado no cadastro.",
                )
            )
            linha_erros = True

        plano = planos.get(plano_raw.lower()) if plano_raw else None
        if plano_raw and not plano:
            erros.append(
                _erro(
                    linha,
                    "plano_financeiro",
                    "V03",
                    f"Plano Financeiro '{plano_raw}' não encontrado no sistema.",
                )
            )
            linha_erros = True

        if cc and plano:
            db_id = str(plano.db_id or "")
            if db_id.startswith("1"):
                erros.append(
                    _erro(
                        linha,
                        "plano_financeiro",
                        "V04",
                        f"Plano '{plano_raw}' é de receita; esta carga é só despesas.",
                    )
                )
                linha_erros = True
            elif (departamento_id, plano.id) not in dept_planos:
                erros.append(
                    _erro(
                        linha,
                        "plano_financeiro",
                        "V04",
                        f"Plano '{plano_raw}' não está autorizado para o departamento/produto.",
                    )
                )
                linha_erros = True

        if linha_erros or not cc or not plano:
            continue

        chave = (cc.id, plano.id)
        if chave not in agregados:
            agregados[chave] = {
                "produto_id": cc.id,
                "plano_financeiro_id": plano.id,
                **{m: 0.0 for m in MESES_STR},
            }
            origem_linha[chave] = linha
        for mes in MESES_STR:
            agregados[chave][mes] += valores[mes]

    validas: List[Dict] = []
    for chave, item in agregados.items():
        item["total_anual"] = sum(item[m] for m in MESES_STR)
        if item["total_anual"] == 0:
            continue
        item["linha"] = origem_linha[chave]
        validas.append(item)
    return erros, validas


def _alinhar_sequencia_id(db: Session, tabela: str) -> None:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql" or not tabela.isidentifier():
        return
    db.execute(
        text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{tabela}', 'id'),
                COALESCE((SELECT MAX(id) FROM {tabela}), 1),
                (SELECT COUNT(*) > 0 FROM {tabela})
            )
            """
        )
    )


def _persistir_despesas(
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
        db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == doc.id).delete()
    _alinhar_sequencia_id(db, "orcamentos")
    _alinhar_sequencia_id(db, "orcamento_itens")
    _alinhar_sequencia_id(db, "auditoria")
    for linha in linhas_validas:
        db.add(
            OrcamentoItem(
                orcamento_id=orc.id,
                produto_id=linha["produto_id"],
                plano_financeiro_id=linha["plano_financeiro_id"],
                **{m: linha.get(m, 0.0) for m in MESES_STR},
                total_anual=linha.get("total_anual", 0.0),
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
                f"{len(linhas_validas)} linhas importadas via Elaboração do Orçamento "
                f"2027 ({arquivo})"
            ),
            usuario_id=usuario_id,
        )
    )
    return orc.id


def importar_orcamentos_departamentos_2027(
    db: Session,
    usuario_id: int,
    *,
    gravar: bool = False,
    base_dir: Optional[str] = None,
) -> Dict[str, Any]:
    raiz = base_dir or SHAREPOINT_ORCAMENTO_DIR
    relatorio: Dict[str, Any] = {
        "ano": ANO_CARGA,
        "tipo": TIPO_CARGA,
        "gravado": False,
        "base_dir": raiz,
        "departamentos": [],
        "ignorados": [],
        "erro_base": None,
    }
    if not os.path.isdir(raiz):
        relatorio["erro_base"] = f"Pasta não encontrada: {raiz}"
        return relatorio

    ccs, planos, depts, dept_planos = _indexar_cadastro(db)
    vistos = set()

    for item in _achar_arquivos(raiz):
        chave = item["chave"]
        if chave in PASTAS_IGNORADAS:
            relatorio["ignorados"].append(
                {"pasta": item["pasta"], "arquivo": item["arquivo"], "motivo": "pasta descartada"}
            )
            continue
        nome_dept = PASTA_PARA_DEPARTAMENTO.get(chave)
        if not nome_dept:
            relatorio["ignorados"].append(
                {
                    "pasta": item["pasta"],
                    "arquivo": item["arquivo"],
                    "motivo": "pasta sem de-para de departamento",
                }
            )
            continue
        if item["path"] in vistos:
            continue
        vistos.add(item["path"])

        dept = depts.get(nome_dept.strip().lower())
        bloco: Dict[str, Any] = {
            "pasta": item["pasta"],
            "arquivo": item["arquivo"],
            "departamento": nome_dept,
            "departamento_id": dept.id if dept else None,
            "gravado": False,
            "orcamento_id": None,
            "total_linhas": 0,
            "total_validas": 0,
            "total_erros": 0,
            "erros": [],
            "mensagem": None,
        }
        if not dept:
            bloco["mensagem"] = f"Departamento '{nome_dept}' não encontrado no cadastro."
            bloco["total_erros"] = 1
            relatorio["departamentos"].append(bloco)
            continue

        rows, err_aba = ler_aba_fimportacao(item["path"])
        if err_aba:
            bloco["mensagem"] = err_aba
            bloco["total_erros"] = 1
            relatorio["departamentos"].append(bloco)
            continue

        bloco["total_linhas"] = len(rows)
        erros, validas = _validar_linhas(rows, dept.id, ccs, planos, dept_planos)
        bloco["total_erros"] = len(erros)
        bloco["total_validas"] = len(validas)
        bloco["erros"] = erros[:50]
        if erros:
            bloco["mensagem"] = (
                "Importação recusada: a planilha contém erros. Nenhum dado deste departamento foi alterado."
            )
            relatorio["departamentos"].append(bloco)
            continue
        if not validas:
            bloco["mensagem"] = "Nenhuma linha com valor para gravar."
            relatorio["departamentos"].append(bloco)
            continue

        if not gravar:
            bloco["mensagem"] = f"{len(validas)} linha(s) válidas (simulação, nada gravado)."
            relatorio["departamentos"].append(bloco)
            continue

        try:
            oid = _persistir_despesas(db, dept, validas, usuario_id, item["arquivo"])
            db.commit()
            bloco["gravado"] = True
            bloco["orcamento_id"] = oid
            bloco["mensagem"] = f"{len(validas)} linha(s) importada(s) com sucesso."
        except PermissionError as e:
            db.rollback()
            bloco["mensagem"] = str(e)
            bloco["total_erros"] = 1
        except Exception as e:
            db.rollback()
            bloco["mensagem"] = f"Falha ao gravar: {e}"
            bloco["total_erros"] = 1
        relatorio["departamentos"].append(bloco)

    relatorio["gravado"] = gravar and any(d.get("gravado") for d in relatorio["departamentos"])
    return relatorio


def _header_key(valor) -> str:
    return _chave(valor).replace(" ", "_")


def _celulas_da_aba(path: str, chave_aba: str) -> Tuple[Dict[int, Dict[int, Any]], Optional[str]]:
    tmp_copy = None
    rows: Dict[int, Dict[int, Any]] = {}
    try:
        fd, tmp_copy = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
        os.close(fd)
        shutil.copyfile(path, tmp_copy)
        with zipfile.ZipFile(tmp_copy) as z:
            sst = _shared_strings(z)
            target = None
            for s in _list_sheets(z):
                if _chave(s["name"]).replace(" ", "") == chave_aba.replace(" ", ""):
                    target = s
                    break
            if target is None:
                return {}, f"Aba '{chave_aba}' não encontrada."
            if target["xml"] not in z.namelist():
                return {}, f"XML da aba '{chave_aba}' ausente ({target['xml']})."
            root = ET.fromstring(z.read(target["xml"]))
            sheet_data = root.find("m:sheetData", NS)
            for row in sheet_data.findall("m:row", NS):
                ridx = int(row.attrib.get("r", "0"))
                cells: Dict[int, Any] = {}
                for c in row.findall("m:c", NS):
                    col, _ = _col_row(c.attrib.get("r", ""))
                    cells[col] = _cell_value(c, sst)
                if cells:
                    rows[ridx] = cells
    except Exception as e:
        return {}, f"Não foi possível abrir o arquivo: {e}"
    finally:
        if tmp_copy:
            try:
                os.remove(tmp_copy)
            except OSError:
                pass
    return rows, None


def ler_aba_despesas_xlsx(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Lê a aba Despesas (CÓDIGO = id_sienge, DESCRIÇÃO CONTA = plano). Conta 1.xx é receita e é ignorada."""
    rows, err = _celulas_da_aba(path, ABA_DESPESAS_XLSX)
    if err:
        return [], err
    if 1 not in rows:
        return [], "Aba Despesas sem cabeçalho."

    header_row = rows[1]
    hmap = {_header_key(header_row.get(i)): i for i in header_row}
    idx_emp = hmap.get("codigo")
    idx_plano = hmap.get("descricao_conta")
    idx_conta = hmap.get("conta")
    idx_meses = [hmap.get(m) for m in MESES_STR]
    if not idx_emp or not idx_plano:
        return [], "Aba Despesas sem colunas CÓDIGO e/ou DESCRIÇÃO CONTA."
    if any(ix is None for ix in idx_meses):
        return [], "Aba Despesas sem as 12 colunas de mês (Jan–Dez)."

    out: List[Dict[str, Any]] = []
    for ridx in sorted(k for k in rows if k > 1):
        cells = rows[ridx]
        emp = _norm_sienge(cells.get(idx_emp))
        plano = str(cells.get(idx_plano) or "").strip()
        conta = str(cells.get(idx_conta) or "").strip() if idx_conta else ""
        meses = {}
        for mes, ix in zip(MESES_STR, idx_meses):
            raw = cells.get(ix)
            if raw is None or str(raw).strip() == "":
                meses[mes] = 0.0
            else:
                meses[mes] = _to_float(raw)
        if not emp and not plano and not any(v for v in meses.values() if v):
            continue
        if conta.startswith("1"):
            continue
        out.append({"linha": ridx, "empreendimento": emp, "plano_financeiro": plano, **meses})
    return out, None


def _persistir_despesas_merge(
    db: Session,
    dept: Departamento,
    linhas_validas: List[Dict],
    usuario_id: int,
    arquivo: str,
) -> Tuple[int, int, int]:
    """Acrescenta/soma no rascunho existente. Não apaga itens já gravados."""
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

    existentes = {
        (it.produto_id, it.plano_financeiro_id): it
        for it in db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).all()
    }
    _alinhar_sequencia_id(db, "orcamentos")
    _alinhar_sequencia_id(db, "orcamento_itens")
    _alinhar_sequencia_id(db, "auditoria")
    n_novos = 0
    n_somados = 0
    for linha in linhas_validas:
        chave = (linha["produto_id"], linha["plano_financeiro_id"])
        item = existentes.get(chave)
        if item:
            for mes in MESES_STR:
                atual = float(getattr(item, mes) or 0.0)
                setattr(item, mes, atual + float(linha.get(mes) or 0.0))
            item.total_anual = sum(float(getattr(item, mes) or 0.0) for mes in MESES_STR)
            n_somados += 1
        else:
            novo = OrcamentoItem(
                orcamento_id=orc.id,
                produto_id=linha["produto_id"],
                plano_financeiro_id=linha["plano_financeiro_id"],
                **{m: linha.get(m, 0.0) for m in MESES_STR},
                total_anual=linha.get("total_anual", 0.0),
            )
            db.add(novo)
            existentes[chave] = novo
            n_novos += 1
    db.add(
        Auditoria(
            evento="Importacao",
            tabela_afetada="orcamentos",
            registro_id=orc.id,
            campo=None,
            valor_anterior=None,
            novo_valor=(
                f"{n_novos} linha(s) novas e {n_somados} somada(s) via {arquivo} "
                f"no rascunho Controladoria {ANO_CARGA}"
            ),
            usuario_id=usuario_id,
        )
    )
    return orc.id, n_novos, n_somados


def importar_despesas_xlsx_controladoria(
    db: Session,
    usuario_id: int,
    *,
    gravar: bool = False,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    arquivo = path or DESPESAS_XLSX_DEFAULT
    relatorio: Dict[str, Any] = {
        "ano": ANO_CARGA,
        "tipo": TIPO_CARGA,
        "departamento": DEPT_CONTROLADORIA,
        "arquivo": arquivo,
        "gravado": False,
        "orcamento_id": None,
        "total_linhas": 0,
        "total_validas": 0,
        "total_erros": 0,
        "novos": 0,
        "somados": 0,
        "erros": [],
        "mensagem": None,
    }
    if not os.path.isfile(arquivo):
        relatorio["mensagem"] = f"Arquivo não encontrado: {arquivo}"
        relatorio["total_erros"] = 1
        return relatorio

    ccs, planos, depts, dept_planos = _indexar_cadastro(db)
    dept = depts.get(DEPT_CONTROLADORIA.strip().lower())
    if not dept:
        relatorio["mensagem"] = f"Departamento '{DEPT_CONTROLADORIA}' não encontrado no cadastro."
        relatorio["total_erros"] = 1
        return relatorio
    relatorio["departamento_id"] = dept.id

    rows, err_aba = ler_aba_despesas_xlsx(arquivo)
    if err_aba:
        relatorio["mensagem"] = err_aba
        relatorio["total_erros"] = 1
        return relatorio

    relatorio["total_linhas"] = len(rows)
    erros, validas = _validar_linhas(rows, dept.id, ccs, planos, dept_planos)
    relatorio["total_erros"] = len(erros)
    relatorio["total_validas"] = len(validas)
    relatorio["erros"] = erros[:50]
    if erros:
        relatorio["mensagem"] = (
            "Importação recusada: a planilha contém erros. Nenhum dado deste arquivo foi alterado."
        )
        return relatorio
    if not validas:
        relatorio["mensagem"] = "Nenhuma linha de despesa com valor para gravar."
        return relatorio

    if not gravar:
        relatorio["mensagem"] = (
            f"{len(validas)} linha(s) válidas para somar no rascunho da Controladoria (simulação)."
        )
        return relatorio

    try:
        oid, n_novos, n_somados = _persistir_despesas_merge(
            db, dept, validas, usuario_id, os.path.basename(arquivo)
        )
        db.commit()
        relatorio["gravado"] = True
        relatorio["orcamento_id"] = oid
        relatorio["novos"] = n_novos
        relatorio["somados"] = n_somados
        relatorio["mensagem"] = (
            f"{n_novos} linha(s) nova(s) e {n_somados} somada(s) no rascunho da Controladoria."
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
