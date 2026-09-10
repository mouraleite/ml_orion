"""Departamento residual Corporativo (importação SharePoint / carga sem dono)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.forecast import Forecast
from app.services.corporativo import CORPORATIVO_NOME, ensure_corporativo_departamento

logger = logging.getLogger(__name__)

CONSOLIDADO_SIENGE_NOME = CORPORATIVO_NOME
CARGA_INICIAL_DESCRICAO = "Carga Inicial Sienge 2026"
IMPORT_ANO = 2026


def ensure_consolidado_sienge_departamento(db: Session) -> Departamento:
    return ensure_corporativo_departamento(db)


def _count_orcamento_itens(db: Session, orcamento_id: int, tipo: str) -> int:
    if tipo == "VENDAS":
        return db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orcamento_id).count()
    return db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orcamento_id).count()


def fix_orcamentos_sharepoint_sem_departamento(db: Session) -> int:
    """Atribui dept. Corporativo a orçamentos importados sem departamento_id."""
    consolidado = ensure_consolidado_sienge_departamento(db)
    changed = 0

    orcamentos = (
        db.query(Orcamento)
        .filter(
            Orcamento.descricao == CARGA_INICIAL_DESCRICAO,
            Orcamento.departamento_id.is_(None),
        )
        .all()
    )
    for o in orcamentos:
        o.departamento_id = consolidado.id
        logger.info("Orçamento %s (%s) → departamento Corporativo", o.id, o.tipo)
        changed += 1

    # Carga legada 2026 (descricao genérica) ainda presa a outro dept. ou sem dept.
    for o in db.query(Orcamento).filter(
        Orcamento.ano == IMPORT_ANO,
        Orcamento.status != "Substituído",
        Orcamento.departamento_id.is_(None),
    ).all():
        o.departamento_id = consolidado.id
        changed += 1

    for tipo in ("DESPESAS", "RECEITAS", "VENDAS"):
        ja_no_sienge = (
            db.query(Orcamento.id)
            .filter(
                Orcamento.ano == IMPORT_ANO,
                Orcamento.tipo == tipo,
                Orcamento.status != "Substituído",
                Orcamento.departamento_id == consolidado.id,
            )
            .first()
        )
        if ja_no_sienge:
            continue

        candidatos = (
            db.query(Orcamento)
            .filter(
                Orcamento.ano == IMPORT_ANO,
                Orcamento.tipo == tipo,
                Orcamento.status != "Substituído",
                Orcamento.departamento_id != consolidado.id,
            )
            .order_by(Orcamento.id)
            .all()
        )
        for o in candidatos:
            if _count_orcamento_itens(db, o.id, tipo) <= 0:
                continue
            o.departamento_id = consolidado.id
            logger.info(
                "Orçamento legado %s (%s, id=%s) → Corporativo",
                o.descricao,
                o.tipo,
                o.id,
            )
            changed += 1
            break

    if changed:
        db.commit()
    return changed


def fix_forecasts_sharepoint_sem_departamento(db: Session) -> int:
    """Atribui Corporativo a forecasts importados sem departamento."""
    consolidado = ensure_consolidado_sienge_departamento(db)
    forecasts = (
        db.query(Forecast)
        .filter(
            Forecast.ano == IMPORT_ANO,
            Forecast.status != "Substituído",
            Forecast.departamento_id.is_(None),
        )
        .all()
    )
    for f in forecasts:
        f.departamento_id = consolidado.id
        logger.info("Forecast %s (%s) → Corporativo", f.id, f.tipo)
    if forecasts:
        db.commit()
    return len(forecasts)


def ensure_sharepoint_departamento_vinculos(db: Session) -> None:
    fix_orcamentos_sharepoint_sem_departamento(db)
    fix_forecasts_sharepoint_sem_departamento(db)