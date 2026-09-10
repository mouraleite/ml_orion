"""Vigência do % societário. Sem faixas, o motor atual não muda."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.company import CompanyOwnershipLink, CompanyOwnershipPeriod
from app.services.mldu_ownership import get_root_company

_YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class PeriodoInvalido(ValueError):
    pass


def parse_ym(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    if not _YM.match(value):
        raise PeriodoInvalido("Mês de vigência deve ser AAAA-MM.")
    return int(value[:4]), int(value[5:7])


def prev_month(ym: str) -> str:
    parsed = parse_ym(ym)
    if not parsed:
        raise PeriodoInvalido("Mês de vigência deve ser AAAA-MM.")
    year, month = parsed
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def ym_tuple(ano: int, mes: int) -> tuple[int, int]:
    return int(ano), int(mes)


def period_covers(period: CompanyOwnershipPeriod, ano: int, mes: int) -> bool:
    target = ym_tuple(ano, mes)
    start = parse_ym(period.valid_from)
    end = parse_ym(period.valid_until)
    if start and target < start:
        return False
    if end and target > end:
        return False
    return True


def percentage_as_of(link: CompanyOwnershipLink, periods: list[CompanyOwnershipPeriod], ano: int, mes: int) -> float:
    if not periods:
        return float(link.percentage)
    covering = [p for p in periods if period_covers(p, ano, mes)]
    if covering:
        covering.sort(key=lambda p: p.valid_from or "")
        return float(covering[-1].percentage)
    earlier = []
    target = ym_tuple(ano, mes)
    for period in periods:
        end = parse_ym(period.valid_until)
        start = parse_ym(period.valid_from)
        last = end or start
        if last and last < target:
            earlier.append(period)
    if earlier:
        earlier.sort(key=lambda p: p.valid_until or p.valid_from or "")
        return float(earlier[-1].percentage)
    periods_sorted = sorted(periods, key=lambda p: p.valid_from or "")
    return float(periods_sorted[0].percentage)


def serialize_periods(periods: list[CompanyOwnershipPeriod]) -> list[dict[str, Any]]:
    ordered = sorted(periods, key=lambda p: (p.valid_from or "", p.id or 0))
    return [
        {
            "id": p.id,
            "percentage": p.percentage,
            "valid_from": p.valid_from,
            "valid_until": p.valid_until,
            "notes": p.notes,
        }
        for p in ordered
    ]


def list_periods_for_link(db: Session, link_id: int) -> list[CompanyOwnershipPeriod]:
    return (
        db.query(CompanyOwnershipPeriod)
        .filter(CompanyOwnershipPeriod.link_id == link_id)
        .order_by(CompanyOwnershipPeriod.valid_from.asc())
        .all()
    )


def record_percentage_change(db: Session, link: CompanyOwnershipLink, new_pct: float, valid_from: str) -> None:
    parse_ym(valid_from)
    old_pct = float(link.percentage)
    if abs(old_pct - float(new_pct)) < 1e-9:
        return

    until = prev_month(valid_from)
    existing = list_periods_for_link(db, link.id)
    start_new = parse_ym(valid_from)

    for period in existing:
        open_start = parse_ym(period.valid_from)
        if period.valid_until is None and open_start and start_new <= open_start:
            raise PeriodoInvalido("O mês de início deve ser posterior ao início da faixa atual.")

    if not existing:
        db.add(
            CompanyOwnershipPeriod(
                link_id=link.id,
                percentage=old_pct,
                valid_from=None,
                valid_until=until,
            )
        )
    else:
        for period in existing:
            if period.valid_until is None:
                period.valid_until = until

    db.add(
        CompanyOwnershipPeriod(
            link_id=link.id,
            percentage=float(new_pct),
            valid_from=valid_from,
            valid_until=None,
        )
    )
    link.percentage = float(new_pct)


def compute_effective_as_of(db: Session, ano: int, mes: int) -> dict[int, float]:
    links = db.query(CompanyOwnershipLink).all()
    periods = db.query(CompanyOwnershipPeriod).all()
    by_link: dict[int, list[CompanyOwnershipPeriod]] = defaultdict(list)
    for period in periods:
        by_link[period.link_id].append(period)

    children: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for link in links:
        pct = percentage_as_of(link, by_link.get(link.id, []), ano, mes)
        children[link.parent_company_id].append((link.child_company_id, pct))

    root = get_root_company(db)
    if not root:
        return {}

    effective: dict[int, float] = {root.id: 100.0}

    def walk(company_id: int, eff_pct: float) -> None:
        for child_id, pct in children.get(company_id, []):
            child_eff = eff_pct * pct / 100.0
            effective[child_id] = child_eff
            walk(child_id, child_eff)

    walk(root.id, 100.0)
    return effective
