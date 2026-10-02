"""Cálculo de participação efetiva MLDU na árvore societária (Onda B)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.company import Company, CompanyOwnershipLink, CompanyOwnershipPeriod, CompanyPartner

ROOT_SIENGE_ID = "1"


def get_root_company(db: Session) -> Company | None:
    return db.query(Company).filter(Company.id_sienge == ROOT_SIENGE_ID).first()


def would_create_cycle(db: Session, parent_id: int, child_id: int, exclude_link_id: int | None = None) -> bool:
    if parent_id == child_id:
        return True

    current = parent_id
    visited: set[int] = set()
    while current is not None:
        if current == child_id:
            return True
        if current in visited:
            break
        visited.add(current)
        q = db.query(CompanyOwnershipLink).filter(CompanyOwnershipLink.child_company_id == current)
        if exclude_link_id is not None:
            q = q.filter(CompanyOwnershipLink.id != exclude_link_id)
        link = q.first()
        current = link.parent_company_id if link else None
    return False


def child_has_other_parent(
    db: Session, child_id: int, exclude_link_id: int | None = None
) -> CompanyOwnershipLink | None:
    q = db.query(CompanyOwnershipLink).filter(CompanyOwnershipLink.child_company_id == child_id)
    if exclude_link_id is not None:
        q = q.filter(CompanyOwnershipLink.id != exclude_link_id)
    return q.first()


def compute_effective_map(db: Session) -> tuple[dict[int, float], dict[int, list[tuple[int, float]]]]:
    """Retorna % efetivo e cadeia de participações por company_id."""
    links = db.query(CompanyOwnershipLink).all()
    children: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for link in links:
        children[link.parent_company_id].append((link.child_company_id, link.percentage))

    root = get_root_company(db)
    if not root:
        return {}, {}

    effective: dict[int, float] = {root.id: 100.0}
    paths: dict[int, list[tuple[int, float]]] = {root.id: []}

    def walk(company_id: int, eff_pct: float, path_chain: list[tuple[int, float]]) -> None:
        for child_id, pct in children.get(company_id, []):
            child_eff = eff_pct * pct / 100.0
            effective[child_id] = child_eff
            child_path = path_chain + [(company_id, pct)]
            paths[child_id] = child_path
            walk(child_id, child_eff, child_path)

    walk(root.id, 100.0, [])
    return effective, paths


def format_calculation_tooltip(path_chain: list[tuple[int, float]]) -> str:
    if not path_chain:
        return "100% (raiz MLDU)"
    parts = [f"{pct:g}%" for _, pct in path_chain]
    running = 100.0
    for _, pct in path_chain:
        running = running * pct / 100.0
    return f"{' × '.join(parts)} = {running:.4g}%"


def effective_for_company(company: Company) -> float:
    if company.usa_participacao_manual and company.participacao_mldu_manual is not None:
        return float(company.participacao_mldu_manual)
    if company.participacao_mldu_efetiva is not None:
        return float(company.participacao_mldu_efetiva)
    return 0.0


def sync_company_effective_percentages(db: Session) -> dict[int, float]:
    effective, _ = compute_effective_map(db)
    root = get_root_company(db)
    companies = db.query(Company).all()

    for company in companies:
        if root and company.id == root.id:
            company.participacao_mldu_efetiva = 100.0
        elif company.id in effective:
            company.participacao_mldu_efetiva = round(effective[company.id], 6)
        else:
            company.participacao_mldu_efetiva = 0.0

    db.commit()
    return effective


def serialize_company_brief(company: Company) -> dict[str, Any]:
    eff = effective_for_company(company)
    return {
        "company_id": company.id,
        "id_sienge": company.id_sienge,
        "nome_fantasia": company.nome_fantasia or company.razao_social,
        "razao_social": company.razao_social,
        "participacao_efetiva": round(eff, 6),
        "participacao_calculada": company.participacao_mldu_efetiva,
        "participacao_manual": company.participacao_mldu_manual,
        "usa_participacao_manual": bool(company.usa_participacao_manual),
        "fonte": "manual" if company.usa_participacao_manual else "calculado",
    }


def ensure_structural_partners_from_links(db: Session) -> dict[str, Any]:
    """Copia o vínculo da árvore para o sócio do Apoio só quando essa participação ainda não existe.

    Não altera percentual já cadastrado nem o fator da consolidação.
    """
    links = db.query(CompanyOwnershipLink).all()
    partners = (
        db.query(CompanyPartner)
        .filter(CompanyPartner.partner_company_id.isnot(None))
        .all()
    )
    by_edge = {(p.company_id, p.partner_company_id): p for p in partners}
    companies = {c.id: c for c in db.query(Company).all()}
    created = 0
    divergencias: list[dict[str, Any]] = []

    for link in links:
        key = (link.child_company_id, link.parent_company_id)
        existing = by_edge.get(key)
        if existing is None:
            db.add(
                CompanyPartner(
                    company_id=link.child_company_id,
                    tipo="Sócio",
                    partner_company_id=link.parent_company_id,
                    percentage=link.percentage,
                    is_consolidated=bool(link.consolidates),
                )
            )
            created += 1
            continue
        if abs(float(existing.percentage or 0) - float(link.percentage)) > 0.02:
            child = companies.get(link.child_company_id)
            parent = companies.get(link.parent_company_id)
            divergencias.append(
                {
                    "company_id": link.child_company_id,
                    "nome": (child.nome_fantasia or child.razao_social) if child else "Empresa",
                    "pai": (parent.nome_fantasia or parent.razao_social) if parent else "Sócio",
                    "apoio_pct": float(existing.percentage or 0),
                    "consolidacao_pct": float(link.percentage),
                }
            )

    if created:
        db.commit()
    return {"created": created, "divergencias": divergencias}


def _partner_pct_for_link(partners_by_edge: dict, link: CompanyOwnershipLink) -> float:
    partner = partners_by_edge.get((link.child_company_id, link.parent_company_id))
    if partner is None:
        return float(link.percentage)
    return float(partner.percentage or 0)


def apply_structural_partner(db: Session, partner: CompanyPartner) -> None:
    """Sócio empresa→empresa passa a ser o percentual atual da consolidação. Faixas passadas ficam."""
    if not partner.partner_company_id:
        return
    parent_id = partner.partner_company_id
    child_id = partner.company_id
    if would_create_cycle(db, parent_id, child_id):
        raise ValueError("Vínculo criaria ciclo na árvore.")
    existing = child_has_other_parent(db, child_id)
    if existing and existing.parent_company_id != parent_id:
        raise ValueError("Empresa filha já possui outro vínculo pai na árvore MLDU.")
    if existing:
        new_pct = float(partner.percentage or 0)
        if abs(float(existing.percentage) - new_pct) >= 1e-9:
            existing.percentage = new_pct
            from app.services.mldu_ownership_periods import list_periods_for_link

            for period in list_periods_for_link(db, existing.id):
                if period.valid_until is None:
                    period.percentage = new_pct
    else:
        db.add(
            CompanyOwnershipLink(
                parent_company_id=parent_id,
                child_company_id=child_id,
                percentage=float(partner.percentage or 0),
                consolidates=bool(partner.is_consolidated),
            )
        )
    sync_company_effective_percentages(db)


def remove_structural_partner(db: Session, partner: CompanyPartner) -> None:
    if not partner.partner_company_id:
        return
    link = (
        db.query(CompanyOwnershipLink)
        .filter(
            CompanyOwnershipLink.child_company_id == partner.company_id,
            CompanyOwnershipLink.parent_company_id == partner.partner_company_id,
        )
        .first()
    )
    if link:
        db.delete(link)
    sync_company_effective_percentages(db)


def build_tree(db: Session) -> dict[str, Any]:
    cadastro = ensure_structural_partners_from_links(db)
    links = db.query(CompanyOwnershipLink).all()
    companies = {c.id: c for c in db.query(Company).all()}
    effective, paths = compute_effective_map(db)
    partners_by_edge = {
        (p.company_id, p.partner_company_id): p
        for p in db.query(CompanyPartner).filter(CompanyPartner.partner_company_id.isnot(None)).all()
    }
    from app.services.mldu_ownership_periods import serialize_periods

    periods_by_link: dict[int, list] = defaultdict(list)
    for period in db.query(CompanyOwnershipPeriod).all():
        periods_by_link[period.link_id].append(period)

    children_map: dict[int, list[CompanyOwnershipLink]] = defaultdict(list)
    for link in links:
        children_map[link.parent_company_id].append(link)

    for parent_id in children_map:
        children_map[parent_id].sort(
            key=lambda l: (companies.get(l.child_company_id).nome_fantasia or "") if companies.get(l.child_company_id) else ""
        )

    def node_from_link(link: CompanyOwnershipLink) -> dict[str, Any]:
        child = companies.get(link.child_company_id)
        if not child:
            return {}
        path = paths.get(child.id, [])
        child_nodes = []
        for child_link in children_map.get(child.id, []):
            n = node_from_link(child_link)
            if n:
                child_nodes.append(n)
        return {
            "link_id": link.id,
            "percentage": _partner_pct_for_link(partners_by_edge, link),
            "consolidates": link.consolidates,
            "notes": link.notes,
            "historico": serialize_periods(periods_by_link.get(link.id, [])),
            **serialize_company_brief(child),
            "calculo_tooltip": format_calculation_tooltip(path),
            "children": child_nodes,
        }

    root = get_root_company(db)
    if not root:
        return {"root": None, "message": f"Empresa raiz (id_sienge={ROOT_SIENGE_ID}) não encontrada. Sincronize empresas no Apoio."}

    root_data = {
        **serialize_company_brief(root),
        "calculo_tooltip": "100% (raiz MLDU)",
        "children": [n for link in children_map.get(root.id, []) if (n := node_from_link(link))],
    }

    linked_child_ids = {link.child_company_id for link in links}
    linked_ids = set(linked_child_ids) | ({root.id} if root else set())
    unlinked = [
        serialize_company_brief(c)
        for c in companies.values()
        if c.id not in linked_ids and c.id_sienge != ROOT_SIENGE_ID
    ]

    return {
        "root": root_data,
        "empresas_sem_vinculo": unlinked,
        "divergencias": cadastro["divergencias"],
    }


# Referência organograma (MLES = 33% conforme decisão do usuário)
SEED_LINKS: list[tuple[str, str, float]] = [
    ("1", "12", 50.0),
    ("12", "13", 55.498),
    ("1", "6", 50.0),
    ("1", "16", 35.0),
    ("16", "21", 68.0),
    ("1", "15", 35.0),
    ("15", "28", 64.5),
    ("1", "17", 25.0),
    ("1", "32", 100.0),
    ("1", "4", 28.0953),
    ("1", "5", 33.0),
]


def seed_reference_links(db: Session) -> dict[str, Any]:
    """Cria vínculos de referência quando empresas existem (id_sienge)."""
    by_sienge = {c.id_sienge: c for c in db.query(Company).all()}
    created = 0
    skipped: list[str] = []

    for parent_sienge, child_sienge, pct in SEED_LINKS:
        parent = by_sienge.get(parent_sienge)
        child = by_sienge.get(child_sienge)
        if not parent or not child:
            skipped.append(f"{parent_sienge}→{child_sienge}")
            continue
        existing = child_has_other_parent(db, child.id)
        if existing:
            skipped.append(f"{parent_sienge}→{child_sienge} (filha já vinculada)")
            continue
        if would_create_cycle(db, parent.id, child.id):
            skipped.append(f"{parent_sienge}→{child_sienge} (ciclo)")
            continue
        db.add(
            CompanyOwnershipLink(
                parent_company_id=parent.id,
                child_company_id=child.id,
                percentage=pct,
                consolidates=True,
            )
        )
        created += 1

    db.commit()
    sync_company_effective_percentages(db)
    return {"created": created, "skipped": skipped}
