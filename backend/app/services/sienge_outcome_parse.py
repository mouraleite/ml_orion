"""
Parse Contas a Pagar (bulk outcome): alinhado ao consolidado SP-MIG.

Critério de realizado (despesas):
  Filtra payments por operationTypeId ∈ {1, 8} (Pagamento + Abatimento).
  Substituição (5) fica fora.
  Adiantamento (10) entra apenas na categoria "Adiantamento a Parceiros"
  e só em título sem rateio entre centros de custo (rate 100%): são os
  adiantamentos que o SP lança como desembolso. Nos títulos rateados
  (parcerias rotativas) o SP lança variação de saldo, não caixa — incluí-los
  infla o realizado.
  Valor do pagamento: grossAmount × rateio (SP usa bruto; retenções
  entram à parte via bankMovements).
  Retenções: bankMovements (historicName / categorias redutoras).

  source_id inclui data do pagamento e id do movimento bancário (evita colisão
  quando o mesmo título paga em meses distintos — ou várias vezes no mesmo dia —
  sempre com sequencialNumber = 1).
"""
from __future__ import annotations

from typing import Any, Dict, Iterator

OPERATION_PAGAMENTO = 1
OPERATION_SUBSTITUICAO = 5
OPERATION_ABATIMENTO_ADIANTAMENTO = 8
OPERATION_ADIANTAMENTO = 10

REALIZADO_OPERATION_IDS = frozenset({
    OPERATION_PAGAMENTO,
    OPERATION_ABATIMENTO_ADIANTAMENTO,
})

# Única categoria em que Adiantamento (op 10) conta como realizado no SP.
ADIANTAMENTO_CATEGORIA_REALIZADO = "adiantamento a parceiros"
RATEIO_INTEGRAL_MIN = 0.999

_OPERATION_NAMES = {
    OPERATION_PAGAMENTO: "pagamento",
    OPERATION_SUBSTITUICAO: "substituição",
    OPERATION_ABATIMENTO_ADIANTAMENTO: "abatimento de adiantamento",
    OPERATION_ADIANTAMENTO: "adiantamento",
}


def is_realizado_operation(pmt: dict) -> bool:
    """True se operationTypeId é 1 (Pagamento) ou 8 (Abatimento)."""
    op_id = pmt.get("operationTypeId")
    if op_id is not None:
        try:
            return int(op_id) in REALIZADO_OPERATION_IDS
        except (TypeError, ValueError):
            pass
    name = str(pmt.get("operationTypeName") or "").strip().lower()
    return name in {
        _OPERATION_NAMES[OPERATION_PAGAMENTO],
        _OPERATION_NAMES[OPERATION_ABATIMENTO_ADIANTAMENTO],
    }


def is_pagamento(pmt: dict) -> bool:
    """Compatibilidade: somente Pagamento."""
    op_id = pmt.get("operationTypeId")
    if op_id is not None:
        try:
            return int(op_id) == OPERATION_PAGAMENTO
        except (TypeError, ValueError):
            pass
    name = str(pmt.get("operationTypeName") or "").strip().lower()
    return name == "pagamento"


def operation_id(pmt: dict) -> int:
    op_id = pmt.get("operationTypeId")
    if op_id is not None:
        try:
            return int(op_id)
        except (TypeError, ValueError):
            pass
    name = str(pmt.get("operationTypeName") or "").strip().lower()
    for oid, oname in _OPERATION_NAMES.items():
        if name == oname:
            return oid
    return OPERATION_PAGAMENTO


def category_rate_ratio(cat: dict) -> float:
    """Rateio 0–1 a partir de financialCategoryRate (API) ou percentage (legado)."""
    raw = cat.get("financialCategoryRate")
    if raw is None:
        raw = cat.get("percentage")
    if raw is None:
        return 1.0
    try:
        return float(raw) / 100.0
    except (TypeError, ValueError):
        return 1.0


def is_legacy_pmt_source_id(source_id: str | None) -> bool:
    """OUT-{titulo}-PMT-{n} antigo. Não inclui OP1/OP8/OP10 (orçamento lê esses)."""
    sid = source_id or ""
    if not sid.startswith("OUT-") or "-PMT-" not in sid:
        return False
    return "-OP" not in sid


def rateio_pmt_historico_do_cc(categories, cost_center_sienge_id):
    """Fatia 0–1 deste CC no título. None = CC não participa (não gravar título cheio).

    Preferência: financialCategoryRate (mesmo critério do OP1). Se a API não
    mandar essa coluna, usa value/soma dos value; percentage sozinho costuma
    vir 100 em cada CC do rateio e não serve.
    """
    cats = list(categories or [])
    cc_key = str(cost_center_sienge_id)
    matching = [c for c in cats if str(c.get("costCenterId")) == cc_key]
    if not cats:
        return 1.0
    if not matching:
        return None
    if any(c.get("financialCategoryRate") is not None for c in matching):
        ratio = sum(category_rate_ratio(c) for c in matching)
        return ratio if ratio > 0 else None
    total_val = 0.0
    match_val = 0.0
    for c in cats:
        try:
            v = float(c.get("value") or 0)
        except (TypeError, ValueError):
            v = 0.0
        total_val += v
        if str(c.get("costCenterId")) == cc_key:
            match_val += v
    if total_val > 0:
        return match_val / total_val if match_val > 0 else None
    distinct = {str(c.get("costCenterId")) for c in cats if c.get("costCenterId") is not None}
    if len(distinct) <= 1:
        return 1.0
    return 1.0 / len(distinct)


def iter_pmt_historico_lines(item: dict, cost_center_sienge_id: str) -> Iterator[Dict[str, Any]]:
    """Linhas no formato legado OUT-{bill}-PMT-{n} com rateio financialCategoryRate.

    Não gera source_id OP1 — orçamento/forecast não lêem este formato.
    Base do valor: netAmount (o que o PMT antigo gravava) × fatia do CC.
    """
    cats = item.get("paymentsCategories") or item.get("financialCategories") or []
    ratio = rateio_pmt_historico_do_cc(cats, cost_center_sienge_id)
    if ratio is None:
        return
    bill_id = item.get("billId", item.get("documentId"))
    matching = [c for c in cats if str(c.get("costCenterId")) == str(cost_center_sienge_id)]
    cat_name = (matching[0].get("financialCategoryName") if matching else None) or "Obras"
    for pmt in item.get("payments") or []:
        date_str = pmt.get("paymentDate")
        if not date_str:
            continue
        pmt_id = pmt.get("sequencialNumber", pmt.get("id", "0"))
        yield {
            "bill_id": bill_id,
            "pmt_id": pmt_id,
            "payment_date": date_str,
            "category_name": cat_name,
            "value": payment_net_amount(pmt) * ratio,
            "source_id": f"OUT-{bill_id}-PMT-{pmt_id}",
            "creditor_name": item.get("creditorName", item.get("vendorName", "")),
            "document_name": item.get("documentIdentificationName", item.get("title", "")),
            "document_number": item.get("documentNumber", ""),
        }


def is_adiantamento_realizado(cat: dict) -> bool:
    """True se a categoria recebe Adiantamento (op 10) como realizado.

    Só "Adiantamento a Parceiros" em título sem rateio entre CCs.
    """
    name = str(cat.get("financialCategoryName") or "").strip().lower()
    return (
        name == ADIANTAMENTO_CATEGORIA_REALIZADO
        and category_rate_ratio(cat) >= RATEIO_INTEGRAL_MIN
    )


def categorias_realizado_do_pagamento(pmt: dict, cats: list) -> list:
    """Categorias que recebem este pagamento, conforme a operação."""
    if is_realizado_operation(pmt):
        return list(cats)
    if operation_id(pmt) == OPERATION_ADIANTAMENTO:
        return [c for c in cats if is_adiantamento_realizado(c)]
    return []


def payment_gross_amount(pmt: dict) -> float:
    """Bruto do pagamento — SP-MIG usa grossAmount (retenções à parte)."""
    try:
        if pmt.get("grossAmount") is not None:
            return float(pmt.get("grossAmount") or 0)
        return float(pmt.get("netAmount") or 0)
    except (TypeError, ValueError):
        return 0.0


def payment_net_amount(pmt: dict) -> float:
    """Compatibilidade: líquido do pagamento."""
    try:
        return float(pmt.get("netAmount", pmt.get("grossAmount", 0)) or 0)
    except (TypeError, ValueError):
        return 0.0


def _payment_date_key(date_str: str) -> str:
    return str(date_str or "")[:10].replace("-", "")


def payment_unique_key(pmt: dict) -> str:
    """Desempate entre pagamentos do mesmo título, data e sequencialNumber.

    O Sienge devolve sequencialNumber=1 em todos os pagamentos de um título;
    o id do movimento bancário é estável e único por pagamento.
    """
    ids = [
        bm.get("id")
        for bm in (pmt.get("bankMovements") or [])
        if bm.get("id") is not None
    ]
    if ids:
        return str(min(ids, key=lambda x: (str(type(x)), x)))
    auth = str(pmt.get("paymentAuthentication") or "").strip()
    return auth[-12:] if auth else ""


def _nome_departaments_costs(src: dict) -> str | None:
    melhor: tuple[float, str] | None = None
    for dc in src.get("departamentsCosts") or []:
        if not isinstance(dc, dict):
            continue
        nome = str(dc.get("name") or dc.get("departmentName") or "").strip()
        if not nome:
            continue
        try:
            rate = float(dc.get("rate") or 0)
        except (TypeError, ValueError):
            rate = 0.0
        if melhor is None or rate > melhor[0]:
            melhor = (rate, nome)
    return melhor[1] if melhor else None


def _nome_authorizations(src: dict) -> str | None:
    for auth in src.get("authorizations") or []:
        if not isinstance(auth, dict):
            continue
        nome = str(auth.get("name") or auth.get("departmentName") or "").strip()
        if nome:
            return nome
    return None


def authorization_name(*sources: Any) -> str | None:
    """Departamento do título: departamentsCosts.name (bulk Sienge). Fallback: authorizations.name."""
    for src in sources:
        if not isinstance(src, dict):
            continue
        nome = _nome_departaments_costs(src)
        if nome:
            return nome
    for src in sources:
        if not isinstance(src, dict):
            continue
        nome = _nome_authorizations(src)
        if nome:
            return nome
    return None


def _outcome_source_id(bill_id, op: int, pmt_id, payment_date: str, fc_id, uniq: str = "") -> str:
    dt = _payment_date_key(payment_date)
    base = f"OUT-{bill_id}-OP{op}-PMT-{pmt_id}-DT-{dt}"
    if uniq:
        base += f"-BM-{uniq}"
    return f"{base}-FC-{fc_id}"


def _retencao_source_id(bill_id, bm_id, fc_id) -> str:
    return f"OUT-{bill_id}-RET-BM-{bm_id}-FC-{fc_id}"


def _is_retencao_bank_movement(bm: dict) -> bool:
    name = str(bm.get("historicName") or "").lower()
    if "reten" in name:
        return True
    for pc in bm.get("paymentCategories") or []:
        cat = str(pc.get("financialCategoryName") or "").lower()
        if "reten" in cat or "caução" in cat or "caucao" in cat:
            return True
    return False


def _iter_retencao_lines(
    item: dict,
    pmt: dict,
    cost_center_sienge_id: str,
) -> Iterator[Dict[str, Any]]:
    bill_id = item.get("billId", item.get("documentId"))
    date_str = pmt.get("paymentDate")
    if not date_str:
        return

    cc_key = str(cost_center_sienge_id)
    for bm in pmt.get("bankMovements") or []:
        if not _is_retencao_bank_movement(bm):
            continue
        try:
            amount = abs(float(bm.get("amount") or 0))
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            continue

        bm_date = bm.get("bankMovementDate") or date_str
        bm_id = bm.get("id", bm.get("sequencialNumber", "0"))
        for pc in bm.get("paymentCategories") or []:
            if str(pc.get("costCenterId")) != cc_key:
                continue
            fc_id = pc.get("financialCategoryId", "0")
            cat_name = pc.get("financialCategoryName") or "Retenção"
            ratio = category_rate_ratio(pc)
            yield {
                "bill_id": bill_id,
                "pmt_id": pmt.get("sequencialNumber", pmt.get("id", "0")),
                "op_id": 0,
                "fc_id": fc_id,
                "payment_date": str(bm_date)[:10],
                "category_name": cat_name,
                "value": amount * ratio,
                "source_id": _retencao_source_id(bill_id, bm_id, fc_id),
                "creditor_name": item.get("creditorName", item.get("vendorName", "")),
                "document_name": item.get("documentIdentificationName", item.get("title", "")),
                "document_number": item.get("documentNumber", ""),
                "authorization_name": authorization_name(pmt, item),
            }


def iter_outcome_pagamento_lines(
    item: dict,
    cost_center_sienge_id: str,
) -> Iterator[Dict[str, Any]]:
    """Alias: mesmas linhas que iter_outcome_realizado_lines (ops SP)."""
    yield from iter_outcome_realizado_lines(item, cost_center_sienge_id)


def iter_outcome_realizado_lines(
    item: dict,
    cost_center_sienge_id: str,
) -> Iterator[Dict[str, Any]]:
    """
    Expande um título outcome em linhas de pagamento + retenções bancárias.

    source_id pagamento: OUT-{bill}-OP{op}-PMT-{pmt}-DT-{YYYYMMDD}-FC-{fc}
    source_id retenção:  OUT-{bill}-RET-BM-{bm}-FC-{fc}
    """
    cc_key = str(cost_center_sienge_id)
    bill_id = item.get("billId", item.get("documentId"))
    cats = item.get("paymentsCategories") or item.get("financialCategories") or []
    matching = [c for c in cats if str(c.get("costCenterId")) == cc_key]

    if cats and not matching:
        return

    if not matching:
        matching = [{
            "financialCategoryId": "0",
            "financialCategoryName": "Obras",
            "financialCategoryRate": 100,
        }]

    seen_ret: set[str] = set()

    for pmt in item.get("payments") or []:
        for ret_line in _iter_retencao_lines(item, pmt, cost_center_sienge_id):
            sid = ret_line["source_id"]
            if sid in seen_ret:
                continue
            seen_ret.add(sid)
            yield ret_line

        # Ops SP: 1 Pagamento, 8 Abatimento e 10 só em adiantamento não rateado
        cats_pmt = categorias_realizado_do_pagamento(pmt, matching)
        if not cats_pmt:
            continue
        date_str = pmt.get("paymentDate")
        if not date_str:
            continue
        gross = payment_gross_amount(pmt)
        pmt_id = pmt.get("sequencialNumber", pmt.get("id", "0"))
        op = operation_id(pmt)
        uniq = payment_unique_key(pmt)
        for cat in cats_pmt:
            ratio = category_rate_ratio(cat)
            fc_id = cat.get("financialCategoryId", "0")
            cat_name = cat.get("financialCategoryName") or "Obras"
            value = gross * ratio
            source_id = _outcome_source_id(bill_id, op, pmt_id, date_str, fc_id, uniq)
            yield {
                "bill_id": bill_id,
                "pmt_id": pmt_id,
                "op_id": op,
                "fc_id": fc_id,
                "payment_date": date_str,
                "category_name": cat_name,
                "value": value,
                "source_id": source_id,
                "creditor_name": item.get("creditorName", item.get("vendorName", "")),
                "document_name": item.get("documentIdentificationName", item.get("title", "")),
                "document_number": item.get("documentNumber", ""),
                "authorization_name": authorization_name(pmt, item),
            }
