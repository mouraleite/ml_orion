"""
Parse Contas a Receber (bulk income):
- Somente receipt operationType Recebimento
- bankMovement E → receita (INCOME)
- bankMovement S → despesa bancária (OUTCOME), tipicamente tarifa de cobrança
- Rateio via financialCategoryRate nas financialCategories do movimento

Critério de realizado (receitas) — alinhado às despesas:
  A tela usa caixa efetivo: receipt Recebimento (op 2) + bankMovement E,
  com rateio financialCategoryRate. Ignora Distrato, Reparcelamento, etc.

  SP-MIG (planilha) pode consolidar outros movimentos; usar SP só como
  conferência, não como fonte do realizado na tela.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from app.services.sienge_outcome_parse import category_rate_ratio

OPERATION_RECEBIMENTO = 2


def is_recebimento(rec: dict) -> bool:
    op_id = rec.get("operationTypeId")
    if op_id is not None:
        try:
            return int(op_id) == OPERATION_RECEBIMENTO
        except (TypeError, ValueError):
            pass
    name = str(rec.get("operationTypeName") or "").strip().lower()
    return name == "recebimento"


def _bm_amount(bm: dict) -> float:
    try:
        return float(bm.get("correctedAmount", bm.get("amount", 0)) or 0)
    except (TypeError, ValueError):
        return 0.0


def _matching_fc(categories: List[dict], cost_center_sienge_id: str) -> List[dict]:
    cc_key = str(cost_center_sienge_id)
    return [c for c in (categories or []) if str(c.get("costCenterId")) == cc_key]


def rateio_previsto_do_cc(categories, cost_center_sienge_id, default_name: str):
    """Fatia do título prevista que pertence a este CC.

    Sem categorias ou sem este centro: None — não grava o valor cheio em todos os CCs.
    """
    matching = _matching_fc(categories or [], cost_center_sienge_id)
    if not matching:
        return None
    ratio = sum(category_rate_ratio(c) for c in matching)
    if ratio <= 0:
        return None
    name = matching[0].get("financialCategoryName") or default_name
    return ratio, name


def iter_income_bank_lines(
    item: dict,
    cost_center_sienge_id: str,
) -> Iterator[Dict[str, Any]]:
    """
    Yields lines with:
      transaction_type: INCOME | OUTCOME
      source_id, payment_date, category_name, value, bill_id, ...
    """
    bill_id = item.get("billId", item.get("documentId"))
    client_name = item.get("clientName", item.get("customerName", item.get("creditorName", "")))
    doc_name = item.get("documentIdentificationName", item.get("title", ""))
    doc_number = item.get("documentNumber", "")

    for rec in item.get("receipts") or []:
        if not is_recebimento(rec):
            continue
        rec_date = rec.get("paymentDate") or rec.get("receiptDate") or rec.get("creditDate")
        rec_id = rec.get("sequencialNumber", rec.get("id", "0"))

        for bm in rec.get("bankMovements") or []:
            op = str(bm.get("operationType") or "").upper()
            if op not in ("E", "S"):
                continue

            date_str = bm.get("bankMovementDate") or rec_date
            if not date_str:
                continue

            amount = abs(_bm_amount(bm))
            bm_id = bm.get("id", bm.get("sequencialNumber", "0"))
            cats = bm.get("financialCategories") or []
            matching = _matching_fc(cats, cost_center_sienge_id)

            if cats and not matching:
                continue
            if not matching:
                # fallback: receiptsCategories do título
                matching = _matching_fc(
                    item.get("receiptsCategories") or [],
                    cost_center_sienge_id,
                )
            if not matching:
                continue

            if op == "E":
                tx_type = "INCOME"
                prefix = "INC"
            else:
                # Pagamento no extrato do recebimento = tarifa / despesa bancária
                tx_type = "OUTCOME"
                prefix = "OUT-TARIFA"

            for cat in matching:
                ratio = category_rate_ratio(cat)
                fc_id = cat.get("financialCategoryId", "0")
                cat_name = cat.get("financialCategoryName") or (
                    "Recebimento" if op == "E" else "Despesas Bancárias"
                )
                source_id = f"{prefix}-{bill_id}-BM-{bm_id}-FC-{fc_id}"
                yield {
                    "transaction_type": tx_type,
                    "bill_id": bill_id,
                    "bm_id": bm_id,
                    "rec_id": rec_id,
                    "fc_id": fc_id,
                    "payment_date": date_str,
                    "category_name": cat_name,
                    "value": amount * ratio,
                    "source_id": source_id,
                    "creditor_name": client_name,
                    "document_name": doc_name,
                    "document_number": doc_number,
                    "historic_name": bm.get("historicName") or "",
                }
