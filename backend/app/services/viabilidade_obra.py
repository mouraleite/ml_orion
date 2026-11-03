"""Vínculo viabilidade (Land Bank) ↔ centro de custo da obra no acompanhamento.

Não calcula KPI. Só decide se o Land Bank ainda deve aparecer na lista.
"""
from __future__ import annotations

from typing import Any


def ids_centros_produtos_acompanhados(db: Any) -> set[int]:
    """Todos os centros do produto quando a cabeça (ou um membro) está rastreada."""
    from app.api.routes.tracking import _mesmo_produto_obra, parse_project_name
    from app.models.cost_center import CostCenter

    tracked = db.query(CostCenter).filter(CostCenter.track_in_dashboard.is_(True)).all()
    ids: set[int] = set()
    seen: set[str] = set()
    for cc in tracked:
        prefix = cc.id_sienge[:3] if cc.id_sienge and len(cc.id_sienge) >= 3 else str(cc.id)
        _city, proj_name = parse_project_name(cc)
        group_key = f"{prefix}_{proj_name}"
        if group_key in seen:
            continue
        seen.add(group_key)
        members = []
        if cc.id_sienge and len(cc.id_sienge) >= 3:
            related = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{prefix}%")).all()
            for rc in related:
                if _mesmo_produto_obra(proj_name, parse_project_name(rc)[1]):
                    members.append(rc)
        if not any(m.id == cc.id for m in members):
            members.append(cc)
        for m in members:
            if m.id is not None:
                ids.add(int(m.id))
    return ids


def land_bank_oculto_por_obra(viability: Any, ids_acompanhados: set[int]) -> bool:
    """True se a viabilidade está ligada a uma obra que já entra como Em Andamento/Encerrado."""
    linked = getattr(viability, "obra_cost_center_id", None)
    if linked is None:
        return False
    return int(linked) in ids_acompanhados
