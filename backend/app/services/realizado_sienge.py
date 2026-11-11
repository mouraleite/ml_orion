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
from sqlalchemy import extract, func, or_

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


def _eh_redutora(plano_id: int, category: str, planos_redutora: Dict[int, Any]) -> bool:
    cat_name = str(category or "").lower()
    return str(planos_redutora.get(plano_id)).strip().upper() == "S" or "reten" in cat_name


def valor_despesa_sienge(
    val: float,
    plano_id: int,
    category: str,
    planos_redutora: Dict[int, Any],
) -> float:
    if _eh_redutora(plano_id, category, planos_redutora):
        return -abs(val or 0.0)
    return val or 0.0


def _consulta_contas_pagar(
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    produto_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
    dept=None,
):
    """(query, filtra_dept_por_parcela) das parcelas pagas; None se o recorte é vazio.

    Única fonte dos filtros: a lista de parcelas e o total agrupado não podem divergir.
    """
    if not produtos_permitidos:
        return None

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
        )

        if eh_diretoria(dept):
            nomes = nomes_autorizacao_do_departamento(db, dept)
            if not nomes:
                return None
            return q.filter(ActualTransaction.authorization_name.in_(nomes)), True

        if not eh_todos(dept) and not eh_residual_leitura(dept):
            nomes = nomes_autorizacao_do_departamento(db, dept)
            if not nomes:
                return None
            return q.filter(ActualTransaction.authorization_name.in_(nomes)), False

        return q, True

    return q, False


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
    consulta = _consulta_contas_pagar(db, ano, produtos_permitidos, produto_id, mes, busca, dept)
    if consulta is None:
        return []
    q, filtra_dept = consulta
    # Linhas leves (só as colunas usadas), sem montar um objeto ORM por parcela:
    # no Realizado de despesas são ~76 mil parcelas no ano (11/11/2026).
    rows = q.with_entities(*_COLUNAS_PARCELA).order_by(ActualTransaction.transaction_date.desc()).all()
    if filtra_dept:
        from app.services.departamento_leitura import parcela_pertence_ao_dept

        pertence: Dict[Optional[str], bool] = {}
        saida = []
        for r in rows:
            auth = r.authorization_name
            if auth not in pertence:
                pertence[auth] = parcela_pertence_ao_dept(db, auth, dept)
            if pertence[auth]:
                saida.append(r)
        return saida
    return rows


_COLUNAS_PARCELA = (
    ActualTransaction.id,
    ActualTransaction.source_id,
    ActualTransaction.cost_center_id,
    ActualTransaction.category,
    ActualTransaction.transaction_date,
    ActualTransaction.value,
    ActualTransaction.creditor_name,
    ActualTransaction.document_name,
    ActualTransaction.document_number,
    ActualTransaction.bill_id,
    ActualTransaction.authorization_name,
)


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
    agrupado: bool = False,
    somente_chaves: bool = False,
) -> None:
    """Soma parcelas OUT-* na matriz (produto_id, plano_id) × mês.

    Padrão: parcela a parcela, na ordem da lista. ``agrupado`` soma no banco
    (mais rápido) e pode mudar o centavo quando o total cai em meio centavo
    (ex.: 2278,575) — aceito só no DFC.
    ``somente_chaves``: só cria as linhas (produto, plano) que têm parcela, sem
    somar valores — para quem precisa apenas das opções de filtro (11/11/2026).
    """
    from app.services.departamento_leitura import (
        eh_residual_leitura,
        eh_todos,
        parcela_pertence_ao_dept,
    )

    planos_id_by_name, planos_redutora = build_planos_maps(db)
    planos_permitidos_set = set(planos_permitidos)
    tocadas: set = set()
    relax_planos = dept is not None and (eh_todos(dept) or eh_residual_leitura(dept))

    consulta = _consulta_contas_pagar(db, ano, produtos_permitidos, dept=dept)
    if consulta is None:
        return
    q, filtra_dept = consulta
    pertence: Dict[Optional[str], bool] = {}

    if somente_chaves:
        combinacoes = (
            q.with_entities(
                ActualTransaction.cost_center_id,
                ActualTransaction.category,
                ActualTransaction.authorization_name,
                func.max(ActualTransaction.transaction_date),
            )
            .group_by(
                ActualTransaction.cost_center_id,
                ActualTransaction.category,
                ActualTransaction.authorization_name,
            )
            .order_by(func.max(ActualTransaction.transaction_date).desc())
            .all()
        )
        for cc_id, category, auth, _ultima in combinacoes:
            plano_id = planos_id_by_name.get(category)
            if not plano_id:
                continue
            if plano_id not in planos_permitidos_set and not relax_planos:
                continue
            if filtra_dept:
                if auth not in pertence:
                    pertence[auth] = parcela_pertence_ao_dept(db, auth, dept)
                if not pertence[auth]:
                    continue
            init_key(cc_id, plano_id)
        return

    linhas = _linhas_realizado(q, agrupado, ActualTransaction.authorization_name)
    for cc_id, category, auth, mes_num, soma, soma_abs in linhas:
        plano_id = planos_id_by_name.get(category)
        if not plano_id:
            continue
        if plano_id not in planos_permitidos_set and not relax_planos:
            continue
        if filtra_dept:
            if auth not in pertence:
                pertence[auth] = parcela_pertence_ao_dept(db, auth, dept)
            if not pertence[auth]:
                continue
        init_key(cc_id, plano_id)
        mes_str = MESES_STR[mes_num - 1]
        val = -soma_abs if _eh_redutora(plano_id, category, planos_redutora) else soma
        matriz[(cc_id, plano_id)]["realizado"][mes_str] += val
        tocadas.add((cc_id, plano_id))
    _arredondar_realizado(matriz, tocadas)


def _arredondar_realizado(matriz: dict, chaves) -> None:
    """Etapa 2 dos centavos: o realizado somado fica em centavos exatos (fecha com o Sienge)."""
    for k in chaves:
        r = matriz[k]["realizado"]
        for m in list(r.keys()):
            r[m] = round(r[m], 2)


def _linhas_realizado(q, agrupado: bool, *extra_cols):
    """(cc, categoria, *extra, mês, soma, soma_abs) — por parcela ou agrupado no banco.

    soma_abs existe porque redutora vale −|valor| por parcela; −|soma| divergiria
    num grupo com sinais mistos.
    """
    if agrupado:
        mes = extract("month", ActualTransaction.transaction_date)
        chaves = (ActualTransaction.cost_center_id, ActualTransaction.category, *extra_cols, mes)
        rows = (
            q.with_entities(
                *chaves,
                func.coalesce(func.sum(ActualTransaction.value), 0.0),
                func.coalesce(func.sum(func.abs(ActualTransaction.value)), 0.0),
            )
            .group_by(*chaves)
            .all()
        )
        for *cabeca, mes_num, soma, soma_abs in rows:
            yield (*cabeca, int(mes_num), float(soma), float(soma_abs))
        return

    for *cabeca, dt, value in _linhas_leves(q, *extra_cols):
        v = value or 0.0
        yield (*cabeca, dt.month, v, abs(v))


def _linhas_leves(q, *extra_cols):
    return (
        q.with_entities(
            ActualTransaction.cost_center_id,
            ActualTransaction.category,
            *extra_cols,
            ActualTransaction.transaction_date,
            ActualTransaction.value,
        )
        .order_by(ActualTransaction.transaction_date.desc())
        .all()
    )


def query_recebimentos_contas_receber(
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    produto_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
) -> List[ActualTransaction]:
    """Recebimentos Sienge: INC-* + BM-* (Contas a Receber + Caixa e Bancos)."""
    q = _consulta_recebimentos(db, ano, produtos_permitidos, produto_id, mes, busca)
    if q is None:
        return []
    rows = q.order_by(ActualTransaction.transaction_date.desc()).all()
    return [r for r in rows if not categoria_excluida_receita_realizado(r.category)]


def _consulta_recebimentos(
    db: Session,
    ano: int,
    produtos_permitidos: List[int],
    produto_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
):
    if not produtos_permitidos:
        return None

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
    return q


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
    agrupado: bool = False,
) -> None:
    """Soma recebimentos INC-* + BM-* na matriz (produto_id, plano_id) × mês."""
    planos_id_by_name, planos_redutora = build_planos_maps(db)
    planos_permitidos_set = set(planos_permitidos)
    tocadas: set = set()

    q = _consulta_recebimentos(db, ano, produtos_permitidos)
    if q is None:
        return
    for cc_id, category, mes_num, soma, soma_abs in _linhas_realizado(q, agrupado):
        if categoria_excluida_receita_realizado(category):
            continue
        plano_id = planos_id_by_name.get(category)
        if not plano_id or plano_id not in planos_permitidos_set:
            continue
        init_key(cc_id, plano_id)
        mes_str = MESES_STR[mes_num - 1]
        val = -soma_abs if _eh_redutora(plano_id, category, planos_redutora) else soma
        matriz[(cc_id, plano_id)]["realizado"][mes_str] += val
        tocadas.add((cc_id, plano_id))
    _arredondar_realizado(matriz, tocadas)
