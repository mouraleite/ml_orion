"""
Agregação do realizado na tela de orçamento.

Despesas: Contas a Pagar realizado = Pagamento (OP1), Abatimento (OP8),
Adiantamento a parceiros (OP10), retenções (RET), mais tarifas/AFAC/BM
já alinhados ao SP. Substituição, Cancelamento e o formato antigo
OUT-{titulo}-PMT-* ficam de fora — distorcem o dashboard.
Receitas: INC-* (Contas a Receber Recebimento) + BM-* (Caixa e Bancos — rendimentos etc.).
AFAC em INC-* fica fora do realizado de receitas (no SP é transferência/OUTCOME).

SP-MIG-* é legado da planilha SharePoint (conferência / orçado), não alimenta
mais o realizado das telas de acompanhamento.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import extract, or_

from app.models.actual_transaction import ActualTransaction
from app.models.financial_plan import FinancialPlan
from app.services.periodos import MESES_STR

FONTE_REALIZADO_DESPESAS = "sienge_contas_pagar"
FONTE_REALIZADO_RECEITAS = "sienge_contas_receber_e_caixa_bancos"

# SP trata AFAC como transferência/despesa (OUTCOME), não como receita de caixa.
# INC-* com categoria AFAC (ex.: 73200) fica fora do realizado de receitas.
_CATEGORIAS_EXCLUIDAS_RECEITA_REALIZADO = frozenset({"afac"})

# source_id do parser atual (e fontes SP paralelas). O LIKE OUT-% antigo
# puxava Substituição/Cancelamento no formato OUT-bill-PMT-n.
SOURCE_ID_LIKES_REALIZADO_DESPESA = (
    "OUT-%-OP1-%",
    "OUT-%-OP8-%",
    "OUT-%-OP10-%",
    "OUT-%-RET-%",
    "OUT-TARIFA-%",
    "OUT-AFAC-%",
    "OUT-BM-%",
)


def source_id_realizado_despesa(source_id: Optional[str]) -> bool:
    """True se o source_id é realizado de despesa nas premissas do dashboard."""
    s = source_id or ""
    if s.startswith("OUT-TARIFA-") or s.startswith("OUT-AFAC-") or s.startswith("OUT-BM-"):
        return True
    if not s.startswith("OUT-"):
        return False
    if "-OP1-" in s or "-OP8-" in s or "-OP10-" in s:
        return True
    return "-RET-" in s


def categoria_excluida_receita_realizado(category: Optional[str]) -> bool:
    return str(category or "").strip().lower() in _CATEGORIAS_EXCLUIDAS_RECEITA_REALIZADO


def valor_despesa_sienge(
    val: float,
    plano_id: int,
    category: str,
    planos_redutora: Dict[int, Any],
) -> float:
    cat_name = str(category or "").lower()
    if str(planos_redutora.get(plano_id)).strip().upper() == "S" or "reten" in cat_name:
        return -abs(val or 0.0)
    return val or 0.0


def query_parcelas_contas_pagar(
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    produto_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
    dept=None,
) -> List[ActualTransaction]:
    """Parcelas pagas Sienge nas premissas do dashboard (OP1/OP8/OP10/RET + SP)."""
    if not produtos_permitidos:
        return []

    cc_ids = [produto_id] if produto_id is not None else produtos_permitidos
    q = db.query(ActualTransaction).filter(
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast == False,
        or_(*[ActualTransaction.source_id.like(p) for p in SOURCE_ID_LIKES_REALIZADO_DESPESA]),
        extract("year", ActualTransaction.transaction_date) == ano,
        ActualTransaction.cost_center_id.in_(cc_ids),
    )
    if mes and mes in MESES_STR:
        q = q.filter(
            extract("month", ActualTransaction.transaction_date) == MESES_STR.index(mes) + 1
        )
    if busca:
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                ActualTransaction.creditor_name.ilike(term),
                ActualTransaction.document_name.ilike(term),
                ActualTransaction.document_number.ilike(term),
                ActualTransaction.bill_id.ilike(term),
            )
        )
    if dept is not None:
        from app.services.departamento_leitura import (
            eh_diretoria,
            eh_residual_leitura,
            eh_todos,
            nomes_autorizacao_do_departamento,
            parcela_pertence_ao_dept,
        )

        if eh_diretoria(dept):
            nomes = nomes_autorizacao_do_departamento(db, dept)
            if not nomes:
                return []
            q = q.filter(ActualTransaction.authorization_name.in_(nomes))
            rows = q.order_by(ActualTransaction.transaction_date.desc()).all()
            return [r for r in rows if parcela_pertence_ao_dept(db, r.authorization_name, dept)]

        if not eh_todos(dept) and not eh_residual_leitura(dept):
            nomes = nomes_autorizacao_do_departamento(db, dept)
            if not nomes:
                return []
            q = q.filter(ActualTransaction.authorization_name.in_(nomes))
            return q.order_by(ActualTransaction.transaction_date.desc()).all()

        rows = q.order_by(ActualTransaction.transaction_date.desc()).all()
        return [r for r in rows if parcela_pertence_ao_dept(db, r.authorization_name, dept)]

    return q.order_by(ActualTransaction.transaction_date.desc()).all()


def build_planos_maps(db: Session) -> Tuple[Dict[str, int], Dict[int, Any]]:
    planos = db.query(FinancialPlan).all()
    return (
        {p.name: p.id for p in planos},
        {p.id: p.fl_redutora for p in planos},
    )


def agregar_realizado_despesas_sienge(
    matriz: dict,
    init_key,
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    planos_permitidos: List[int],
    dept=None,
) -> None:
    """Soma parcelas OUT-* na matriz (produto_id, plano_id) × mês."""
    from app.services.departamento_leitura import eh_residual_leitura, eh_todos

    planos_id_by_name, planos_redutora = build_planos_maps(db)
    planos_permitidos_set = set(planos_permitidos)
    relax_planos = dept is not None and (eh_todos(dept) or eh_residual_leitura(dept))

    for real in query_parcelas_contas_pagar(db, ano, produtos_permitidos, dept=dept):
        plano_id = planos_id_by_name.get(real.category)
        if not plano_id:
            continue
        if plano_id not in planos_permitidos_set and not relax_planos:
            continue
        init_key(real.cost_center_id, plano_id)
        mes_str = MESES_STR[real.transaction_date.month - 1]
        val = valor_despesa_sienge(real.value, plano_id, real.category, planos_redutora)
        matriz[(real.cost_center_id, plano_id)]["realizado"][mes_str] += val


def query_recebimentos_contas_receber(
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    produto_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
) -> List[ActualTransaction]:
    """Recebimentos Sienge: INC-* + BM-* (Contas a Receber + Caixa e Bancos)."""
    if not produtos_permitidos:
        return []

    cc_ids = [produto_id] if produto_id is not None else produtos_permitidos
    q = db.query(ActualTransaction).filter(
        ActualTransaction.transaction_type == "INCOME",
        ActualTransaction.is_forecast == False,
        or_(
            ActualTransaction.source_id.like("INC-%"),
            ActualTransaction.source_id.like("BM-%"),
        ),
        extract("year", ActualTransaction.transaction_date) == ano,
        ActualTransaction.cost_center_id.in_(cc_ids),
    )
    if mes and mes in MESES_STR:
        q = q.filter(
            extract("month", ActualTransaction.transaction_date) == MESES_STR.index(mes) + 1
        )
    if busca:
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                ActualTransaction.creditor_name.ilike(term),
                ActualTransaction.document_name.ilike(term),
                ActualTransaction.document_number.ilike(term),
                ActualTransaction.bill_id.ilike(term),
            )
        )
    rows = q.order_by(ActualTransaction.transaction_date.desc()).all()
    return [r for r in rows if not categoria_excluida_receita_realizado(r.category)]


def valor_receita_sienge(
    val: float,
    plano_id: int,
    category: str,
    planos_redutora: Dict[int, Any],
) -> float:
    """Mesma regra de redutora usada no orçado/forecast de receitas."""
    return valor_despesa_sienge(val, plano_id, category, planos_redutora)


def agregar_realizado_receitas_sienge(
    matriz: dict,
    init_key,
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    planos_permitidos: List[int],
) -> None:
    """Soma recebimentos INC-* + BM-* na matriz (produto_id, plano_id) × mês."""
    planos_id_by_name, planos_redutora = build_planos_maps(db)
    planos_permitidos_set = set(planos_permitidos)

    for real in query_recebimentos_contas_receber(db, ano, produtos_permitidos):
        plano_id = planos_id_by_name.get(real.category)
        if not plano_id or plano_id not in planos_permitidos_set:
            continue
        init_key(real.cost_center_id, plano_id)
        mes_str = MESES_STR[real.transaction_date.month - 1]
        val = valor_receita_sienge(real.value, plano_id, real.category, planos_redutora)
        matriz[(real.cost_center_id, plano_id)]["realizado"][mes_str] += val
