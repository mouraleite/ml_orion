"""
Parse Caixa e Bancos (bulk bank-movement) — complemento ao Contas a Receber.

Alinhado ao relatório SharePoint (SP-MIG) para categorias que não passam por
/income Recebimento:
  - Rendimentos de Aplicações / Fundos (histórico 52)
  - Descontos Obtidos
  - Reembolso de Despesas Gerais (quando não há INC-* no mesmo CC+mês+categoria)

Critério: movimento entrada (operationType E) × financialCategoryRate.

Despesa (OUTCOME), saída (operationType S):
  - IR sobre Aplicação — retenção do banco sobre rendimento; não passa pelo
    Contas a Pagar. Restrito a essa categoria: qualquer pagamento de título
    também gera saída no extrato, e liberar as demais duplicaria o realizado.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from app.services.sienge_outcome_parse import category_rate_ratio

HISTORIC_RENDIMENTO_APLICACAO = 52

# Únicas categorias de saída do extrato que viram despesa (não há título no CP).
DESPESA_CATEGORIAS_EXTRATO = ("ir sobre aplica",)


def _is_entrada(item: dict) -> bool:
    op = str(item.get("bankMovementOperationType") or "").upper()
    return op in ("", "E")


def _is_saida(item: dict) -> bool:
    return str(item.get("bankMovementOperationType") or "").upper() == "S"


def is_despesa_extrato(category_name: str) -> bool:
    nm = (category_name or "").strip().lower()
    return any(alvo in nm for alvo in DESPESA_CATEGORIAS_EXTRATO)


def _matching_fc(categories: List[dict], cost_center_sienge_id: str) -> List[dict]:
    cc_key = str(cost_center_sienge_id)
    return [c for c in (categories or []) if str(c.get("costCenterId")) == cc_key]


def _bm_amount(item: dict) -> float:
    try:
        return abs(float(item.get("bankMovementAmount") or 0))
    except (TypeError, ValueError):
        return 0.0


def _category_kind(category_name: str, historic_id: Optional[int]) -> Optional[str]:
    """rendimento | desconto | reembolso | duplicidade | None"""
    nm = (category_name or "").lower()
    if "descontos obtidos" in nm:
        return "desconto"
    if "reembolso" in nm:
        return "reembolso"
    if "duplicidade" in nm:
        return "duplicidade"
    if "rendimento" in nm or historic_id == HISTORIC_RENDIMENTO_APLICACAO:
        return "rendimento"
    return None


def build_inc_reembolso_keys(
    inc_by_month_category: Dict[Tuple[int, str], float],
) -> Set[Tuple[int, str]]:
    """Chaves (mês, categoria) com reembolso já coberto por INC-*."""
    return {
        (month, cat)
        for (month, cat), val in inc_by_month_category.items()
        if abs(val) >= 0.01
    }


def build_outcome_cobertura_keys(
    out_by_month_category: Dict[Tuple[int, str], float],
) -> Set[Tuple[int, str]]:
    """Chaves (mês, categoria) já cobertas por Contas a Pagar (OUT-*)."""
    return {
        (month, cat)
        for (month, cat), val in out_by_month_category.items()
        if abs(val) >= 0.01
    }


def iter_bank_movement_despesa_lines(
    item: dict,
    cost_center_sienge_id: str,
    *,
    skip_keys: Optional[Set[Tuple[int, str]]] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Yields OUTCOME lines a partir de saídas do extrato (IR sobre Aplicação).
    source_id: OUT-BM-{bankMovementId}-FC-{fc_id}
    """
    if not _is_saida(item):
        return

    date_str = item.get("bankMovementDate")
    if not date_str:
        return

    try:
        month = int(str(date_str)[5:7])
    except (TypeError, ValueError):
        return

    amount = _bm_amount(item)
    if amount <= 0:
        return

    matching = _matching_fc(item.get("financialCategories") or [], cost_center_sienge_id)
    if not matching:
        return

    bm_id = item.get("bankMovementId", item.get("id", "0"))
    ja_coberto = skip_keys or set()

    for cat in matching:
        cat_name = (cat.get("financialCategoryName") or "").strip()
        if not is_despesa_extrato(cat_name):
            continue
        if (month, cat_name) in ja_coberto:
            continue

        value = amount * category_rate_ratio(cat)
        if value <= 0:
            continue

        fc_id = cat.get("financialCategoryId", "0")
        yield {
            "transaction_type": "OUTCOME",
            "bm_id": bm_id,
            "fc_id": fc_id,
            "payment_date": date_str,
            "category_name": cat_name,
            "value": value,
            "source_id": f"OUT-BM-{bm_id}-FC-{fc_id}",
            "creditor_name": item.get("creditorName") or item.get("clientName") or "",
            "document_name": item.get("documentIdentificationName") or "",
            "document_number": item.get("documentIdentificationNumber") or "",
            "bill_id": str(item.get("billId") or ""),
            "historic_name": item.get("bankMovementHistoricName") or "",
        }


def iter_bank_movement_receita_lines(
    item: dict,
    cost_center_sienge_id: str,
    *,
    skip_reembolso_keys: Optional[Set[Tuple[int, str]]] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Yields INCOME lines from bank-movement for SP-aligned receita categories.
    source_id: BM-{bankMovementId}-FC-{fc_id}
    """
    if not _is_entrada(item):
        return

    date_str = item.get("bankMovementDate")
    if not date_str:
        return

    try:
        month = int(str(date_str)[5:7])
    except (TypeError, ValueError):
        return

    bm_id = item.get("bankMovementId", item.get("id", "0"))
    historic_id = item.get("bankMovementHistoricId")
    try:
        historic_id = int(historic_id) if historic_id is not None else None
    except (TypeError, ValueError):
        historic_id = None

    amount = _bm_amount(item)
    if amount <= 0:
        return

    cats = item.get("financialCategories") or []
    matching = _matching_fc(cats, cost_center_sienge_id)
    if not matching:
        return

    skip_reembolso = skip_reembolso_keys or set()

    for cat in matching:
        cat_name = cat.get("financialCategoryName") or "Recebimento"
        kind = _category_kind(cat_name, historic_id)
        if kind is None:
            continue

        if kind in ("reembolso", "duplicidade") and (month, cat_name.strip()) in skip_reembolso:
            continue

        ratio = category_rate_ratio(cat)
        fc_id = cat.get("financialCategoryId", "0")
        value = amount * ratio
        if value <= 0:
            continue

        yield {
            "transaction_type": "INCOME",
            "bm_id": bm_id,
            "fc_id": fc_id,
            "payment_date": date_str,
            "category_name": cat_name,
            "value": value,
            "source_id": f"BM-{bm_id}-FC-{fc_id}",
            "creditor_name": item.get("clientName") or item.get("creditorName") or "",
            "document_name": item.get("documentIdentificationName") or "",
            "document_number": item.get("documentIdentificationNumber") or "",
            "bill_id": str(item.get("billId") or ""),
            "historic_name": item.get("bankMovementHistoricName") or "",
        }
