"""Validação da árvore MLDU vs organograma de referência (Onda E)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.company import Company, CompanyOwnershipLink
from app.services.mldu_ownership import (
    SEED_LINKS,
    compute_effective_map,
    effective_for_company,
    get_root_company,
)

# % efetivo MLDU esperado (organograma oficial; MLES = 33%, não SharePoint 66%).
REFERENCE_EFFECTIVE_PCT: dict[str, float] = {
    "1": 100.0,
    "12": 50.0,
    "13": 27.749,
    "6": 50.0,
    "16": 35.0,
    "21": 23.8,
    "28": 22.575,
    "32": 100.0,
    "4": 28.0953,
    "5": 33.0,
}

REFERENCE_LINKS: list[tuple[str, str, float]] = list(SEED_LINKS)

TOLERANCE_PCT = 0.02


def _pct_close(actual: float | None, expected: float, tol: float = TOLERANCE_PCT) -> bool:
    if actual is None:
        return False
    return abs(float(actual) - expected) <= tol


def validate_organograma(db: Session) -> dict[str, Any]:
    """
    Compara árvore atual com referência do organograma.
    Empresas ausentes no cadastro são avisos; divergência de % em empresas presentes falha.
    """
    companies = {c.id_sienge: c for c in db.query(Company).all() if c.id_sienge}
    links = db.query(CompanyOwnershipLink).all()

    link_by_child_sienge: dict[str, tuple[str, float]] = {}
    for link in links:
        parent = next((c for c in companies.values() if c.id == link.parent_company_id), None)
        child = next((c for c in companies.values() if c.id == link.child_company_id), None)
        if parent and child and parent.id_sienge and child.id_sienge:
            link_by_child_sienge[child.id_sienge] = (parent.id_sienge, link.percentage)

    effective_map, _ = compute_effective_map(db)
    root = get_root_company(db)

    empresas: list[dict[str, Any]] = []
    vinculos: list[dict[str, Any]] = []
    avisos: list[str] = []
    divergencias = 0

    if not root:
        avisos.append("Empresa raiz MLDU (id_sienge=1) não encontrada. Sincronize empresas no Apoio.")

    for id_sienge, expected_pct in sorted(REFERENCE_EFFECTIVE_PCT.items(), key=lambda x: x[0]):
        company = companies.get(id_sienge)
        if not company:
            empresas.append(
                {
                    "id_sienge": id_sienge,
                    "status": "ausente",
                    "expected_pct": expected_pct,
                    "message": "Empresa não cadastrada/sincronizada.",
                }
            )
            avisos.append(f"Empresa id {id_sienge} ausente no cadastro.")
            continue

        actual_pct = effective_for_company(company)
        calculated = effective_map.get(company.id)
        ok = _pct_close(actual_pct, expected_pct)
        if not ok:
            divergencias += 1

        empresas.append(
            {
                "id_sienge": id_sienge,
                "company_id": company.id,
                "nome": company.nome_fantasia or company.razao_social,
                "status": "ok" if ok else "divergente",
                "expected_pct": expected_pct,
                "actual_pct": round(actual_pct, 6),
                "calculated_pct": round(calculated, 6) if calculated is not None else None,
                "fonte": "manual" if company.usa_participacao_manual else "calculado",
            }
        )

    for parent_sienge, child_sienge, expected_pct in REFERENCE_LINKS:
        parent = companies.get(parent_sienge)
        child = companies.get(child_sienge)
        if not parent or not child:
            vinculos.append(
                {
                    "parent_id_sienge": parent_sienge,
                    "child_id_sienge": child_sienge,
                    "status": "ausente",
                    "expected_pct": expected_pct,
                    "message": "Empresa pai ou filha não cadastrada.",
                }
            )
            continue

        found = link_by_child_sienge.get(child_sienge)
        if not found:
            divergencias += 1
            vinculos.append(
                {
                    "parent_id_sienge": parent_sienge,
                    "child_id_sienge": child_sienge,
                    "status": "faltando",
                    "expected_pct": expected_pct,
                    "message": "Vínculo não existe na árvore.",
                }
            )
            continue

        actual_parent, actual_pct = found
        parent_ok = actual_parent == parent_sienge
        pct_ok = _pct_close(actual_pct, expected_pct)
        ok = parent_ok and pct_ok
        if not ok:
            divergencias += 1

        vinculos.append(
            {
                "parent_id_sienge": parent_sienge,
                "child_id_sienge": child_sienge,
                "status": "ok" if ok else "divergente",
                "expected_pct": expected_pct,
                "actual_pct": actual_pct,
                "actual_parent_id_sienge": actual_parent,
            }
        )

    present_refs = [e for e in empresas if e["status"] != "ausente"]
    ok = divergencias == 0 and root is not None

    return {
        "ok": ok,
        "divergencias": divergencias,
        "empresas": empresas,
        "vinculos": vinculos,
        "avisos": avisos,
        "referencia": {
            "fonte": "Organograma MLDU (MLES 33%)",
            "tolerancia_pct": TOLERANCE_PCT,
            "total_empresas_referencia": len(REFERENCE_EFFECTIVE_PCT),
            "total_vinculos_referencia": len(REFERENCE_LINKS),
        },
    }
