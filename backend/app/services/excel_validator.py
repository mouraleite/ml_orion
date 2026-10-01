"""
excel_validator.py — Validador de planilhas Excel para importação de orçamentos.
Implementa todas as validações da Seção 19.1 (EXC-001, COM-007).
Modo tudo-ou-nada: se qualquer erro ocorrer, nenhuma linha é gravada (DEC-005).
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.services.auth_matrix import validate_budget_allocation
from app.services.periodos import MESES_STR

# ── Colunas esperadas por tipo de orçamento ──────────────────────────────────
COLUNAS_DESPESAS = ["produto", "plano_financeiro"] + MESES_STR
COLUNAS_RECEITAS = ["produto", "plano_financeiro"] + MESES_STR
COLUNAS_VENDAS   = ["produto", "plano_venda", "mes", "numero_vendas", "ticket_medio", "vgv"]


def _erro(linha: int, campo: str, codigo: str, mensagem: str) -> Dict:
    return {"linha": linha, "campo": campo, "codigo": codigo, "mensagem": mensagem}


def _to_float(value) -> Optional[float]:
    """Converte para float de forma segura, retorna None se inválido."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _to_int(value) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ── Validação de Despesas / Receitas ────────────────────────────────────────

def validar_despesas_receitas(
    rows: List[Dict],
    tipo: str,          # "DESPESAS" ou "RECEITAS"
    ano: int,
    departamento_id: int,
    db: Session,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Valida uma lista de linhas e retorna (erros, linhas_validas).
    linhas_validas só é usada se erros estiver vazio (tudo-ou-nada).
    """
    erros: List[Dict] = []
    chaves_vistas: Set[Tuple] = set()
    linhas_validas: List[Dict] = []

    # Cache de lookups
    produtos_por_nome: Dict[str, CostCenter] = {
        p.nome.strip().lower(): p for p in db.query(CostCenter).all() if p.nome
    }
    planos_por_nome: Dict[str, FinancialPlan] = {
        p.name.strip().lower(): p for p in db.query(FinancialPlan).all()
    }

    for i, row in enumerate(rows, start=2):  # linha 2 = primeira de dados (linha 1 = cabeçalho)
        linha_erros = False

        # V01 — Campos obrigatórios
        produto_raw = str(row.get("produto", "") or "").strip()
        plano_raw   = str(row.get("plano_financeiro", "") or "").strip()

        if not produto_raw:
            erros.append(_erro(i, "produto", "V01", "Campo obrigatório 'produto' está vazio."))
            linha_erros = True
        if not plano_raw:
            erros.append(_erro(i, "plano_financeiro", "V01", "Campo obrigatório 'plano_financeiro' está vazio."))
            linha_erros = True

        # V02 — Produto inexistente
        produto_obj = produtos_por_nome.get(produto_raw.lower()) if produto_raw else None
        if produto_raw and not produto_obj:
            erros.append(_erro(i, "produto", "V02", f"Produto '{produto_raw}' não encontrado no sistema."))
            linha_erros = True

        # V03 — Plano Financeiro inexistente
        plano_obj = planos_por_nome.get(plano_raw.lower()) if plano_raw else None
        if plano_raw and not plano_obj:
            erros.append(_erro(i, "plano_financeiro", "V03", f"Plano Financeiro '{plano_raw}' não encontrado no sistema."))
            linha_erros = True

        # V04 — Plano não autorizado (só se produto e plano existem)
        if produto_obj and plano_obj:
            autorizado = validate_budget_allocation(db, departamento_id, produto_obj.id, plano_obj.id)
            if not autorizado:
                erros.append(_erro(i, "plano_financeiro", "V04",
                    f"Plano '{plano_raw}' não está autorizado para o departamento/produto."))
                linha_erros = True

        # V05 — Ano inválido
        if not (2000 <= ano <= 2099):
            erros.append(_erro(i, "ano", "V05", f"Ano '{ano}' inválido (esperado 2000–2099)."))
            linha_erros = True

        # V06 — Valores mensais inválidos ou negativos
        valores_mensais: Dict[str, float] = {}
        for mes in MESES_STR:
            raw = row.get(mes, 0)
            v = _to_float(raw)
            if v is None:
                erros.append(_erro(i, mes, "V06", f"Valor inválido na coluna '{mes}': '{raw}'."))
                linha_erros = True
            else:
                valores_mensais[mes] = v

        # V07 — Duplicidade
        if produto_obj and plano_obj:
            chave = (produto_obj.id, plano_obj.id)
            if chave in chaves_vistas:
                erros.append(_erro(i, "produto/plano_financeiro", "V07",
                    f"Combinação Produto='{produto_raw}' + Plano='{plano_raw}' duplicada na planilha."))
                linha_erros = True
            else:
                chaves_vistas.add(chave)

        if not linha_erros and produto_obj and plano_obj:
            linhas_validas.append({
                "produto_id": produto_obj.id,
                "plano_financeiro_id": plano_obj.id,
                **valores_mensais,
                "total_anual": sum(valores_mensais.values()),
            })

    return erros, linhas_validas


# ── Validação de Vendas ──────────────────────────────────────────────────────

def validar_vendas(
    rows: List[Dict],
    ano: int,
    departamento_id: int,
    db: Session,
) -> Tuple[List[Dict], List[Dict]]:
    """Valida planilha de Vendas. Retorna (erros, linhas_validas)."""
    erros: List[Dict] = []
    chaves_vistas: Set[Tuple] = set()
    linhas_validas: List[Dict] = []

    produtos_por_nome = {p.nome.strip().lower(): p for p in db.query(CostCenter).all() if p.nome}
    planos_por_nome   = {p.nome.strip().lower(): p for p in db.query(PaymentPlan).all() if p.nome}

    for i, row in enumerate(rows, start=2):
        linha_erros = False

        produto_raw  = str(row.get("produto", "") or "").strip()
        plano_raw    = str(row.get("plano_venda", "") or "").strip()
        mes_raw      = row.get("mes")
        num_raw      = row.get("numero_vendas", 0)
        ticket_raw   = row.get("ticket_medio", 0)
        vgv_raw      = row.get("vgv", 0)

        # V01 — Campos obrigatórios
        for campo, val in [("produto", produto_raw), ("plano_venda", plano_raw), ("mes", mes_raw)]:
            if not val and val != 0:
                erros.append(_erro(i, campo, "V01", f"Campo obrigatório '{campo}' está vazio."))
                linha_erros = True

        # V02 — Produto
        produto_obj = produtos_por_nome.get(produto_raw.lower()) if produto_raw else None
        if produto_raw and not produto_obj:
            erros.append(_erro(i, "produto", "V02", f"Produto '{produto_raw}' não encontrado."))
            linha_erros = True

        # V03 — Plano de Venda
        plano_obj = planos_por_nome.get(plano_raw.lower()) if plano_raw else None
        if plano_raw and not plano_obj:
            erros.append(_erro(i, "plano_venda", "V03", f"Plano de Venda '{plano_raw}' não encontrado."))
            linha_erros = True

        # V05 — Mês inválido
        mes_int = _to_int(mes_raw)
        if mes_int is None or not (1 <= mes_int <= 12):
            erros.append(_erro(i, "mes", "V05", f"Mês '{mes_raw}' inválido (esperado 1–12)."))
            linha_erros = True

        if not (2000 <= ano <= 2099):
            erros.append(_erro(i, "ano", "V05", f"Ano '{ano}' inválido."))
            linha_erros = True

        # V06 — Valores numéricos
        numero_vendas = _to_int(num_raw)
        ticket_medio  = _to_float(ticket_raw)
        vgv           = _to_float(vgv_raw)

        is_distrato = bool(plano_obj and "distrato" in (plano_obj.nome or "").lower())

        if numero_vendas is None or (numero_vendas < 0 and not is_distrato):
            erros.append(_erro(i, "numero_vendas", "V06", f"Número de vendas inválido: '{num_raw}'."))
            linha_erros = True
        elif is_distrato and numero_vendas > 0:
            numero_vendas = -numero_vendas

        if ticket_medio is None or ticket_medio < 0:
            erros.append(_erro(i, "ticket_medio", "V06", f"Ticket médio inválido: '{ticket_raw}'."))
            linha_erros = True

        if vgv is None or (vgv < 0 and not is_distrato):
            erros.append(_erro(i, "vgv", "V06", f"VGV inválido: '{vgv_raw}'."))
            linha_erros = True
        elif is_distrato and vgv > 0:
            vgv = -vgv

        # V07 — Duplicidade
        if produto_obj and plano_obj and mes_int:
            chave = (produto_obj.id, plano_obj.id, mes_int)
            if chave in chaves_vistas:
                erros.append(_erro(i, "produto/plano_venda/mes", "V07",
                    f"Combinação Produto+Plano+Mês duplicada na linha {i}."))
                linha_erros = True
            else:
                chaves_vistas.add(chave)

        if not linha_erros and produto_obj and plano_obj and mes_int is not None:
            linhas_validas.append({
                "produto_id":    produto_obj.id,
                "plano_venda_id": plano_obj.id,
                "mes":           mes_int,
                "ano":           ano,
                "numero_vendas": numero_vendas or 0,
                "ticket_medio":  ticket_medio or 0.0,
                "vgv":           vgv or 0.0,
            })

    return erros, linhas_validas


# ── Leitura de arquivo Excel ─────────────────────────────────────────────────

def ler_excel(conteudo: bytes, tipo: str) -> Tuple[List[Dict], List[str]]:
    """
    Lê o arquivo Excel e retorna (rows, colunas_encontradas).
    Normaliza cabeçalhos (lowercase, sem espaços).
    """
    import io
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
        ws = wb.active
    except Exception as e:
        raise ValueError(f"Não foi possível abrir o arquivo Excel: {e}")

    rows_raw = list(ws.iter_rows(values_only=True))
    if len(rows_raw) < 2:
        raise ValueError("Planilha vazia ou sem linhas de dados.")

    # Cabeçalho na linha 1
    header = [str(h or "").strip().lower().replace(" ", "_") for h in rows_raw[0]]
    rows = []
    for raw in rows_raw[1:]:
        # Ignora linhas totalmente vazias
        if all(v is None or str(v).strip() == "" for v in raw):
            continue
        rows.append(dict(zip(header, raw)))

    return rows, header
