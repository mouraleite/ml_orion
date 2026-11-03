"""Cronograma de desembolso da engenharia Sienge, só no acompanhamento.

Não grava FCST-* / OP1. O realizado e as contas a pagar em aberto ficam intactos.
O que entra aqui é só o saldo do orçamento da obra ainda não comprometido,
a partir do mês seguinte ao corrente.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.services.realizado_sienge import SOURCE_ID_LIKES_REALIZADO_DESPESA
from app.services.sienge_client import api_v1_base_url, get_default_client

logger = logging.getLogger(__name__)

TRK_ENG_PREFIX = "TRK-ENG-"
CATEGORIA_OBRAS = "Obras"


def proximo_mes_yyyy_mm(hoje: date | None = None) -> str:
    dia = hoje or date.today()
    ano, mes = dia.year, dia.month + 1
    if mes > 12:
        ano += 1
        mes = 1
    return f"{ano:04d}-{mes:02d}"


def categoria_do_sheet(descricao: str | None) -> str:
    texto = (descricao or "").lower()
    if "cancelamento" in texto or "devoluç" in texto:
        return "Distratos"
    if "marketing" in texto:
        return "Despesas com Marketing"
    if "comiss" in texto:
        return "Comissões de Vendas"
    if "comerc" in texto or "stand" in texto:
        return "Despesas Comerciais"
    if "projeto" in texto:
        return "Projetos"
    if "área bruta" in texto or "areas brutas" in texto or "terreno" in texto:
        return "Terreno"
    if "infraestrutura" in texto or "infra-estrutura" in texto:
        return CATEGORIA_OBRAS
    if "captação" in texto or "captacao" in texto or "estruturação" in texto or "estruturacao" in texto:
        return "Funding"
    if "administrativ" in texto or "estoque" in texto:
        return "Despesas Administrativas"
    return CATEGORIA_OBRAS


def alocar_cronograma_nao_comprometido(
    cronograma: dict[str, dict[str, float]],
    comprometido: float,
    a_partir_de: str,
) -> dict[str, dict[str, float]]:
    """Escala só os meses futuros para caber o saldo ainda não pago/comprometido."""
    total = sum(float(v or 0) for cats in cronograma.values() for v in cats.values())
    restante = max(0.0, total - max(0.0, float(comprometido or 0)))
    if restante <= 0:
        return {}
    futuro = {
        mes: {cat: float(val or 0) for cat, val in (cats or {}).items() if float(val or 0)}
        for mes, cats in cronograma.items()
        if mes >= a_partir_de
    }
    futuro = {mes: cats for mes, cats in futuro.items() if cats}
    peso = sum(v for cats in futuro.values() for v in cats.values())
    if peso <= 0:
        return {a_partir_de: {CATEGORIA_OBRAS: restante}}
    fator = restante / peso
    out: dict[str, dict[str, float]] = {}
    for mes, cats in futuro.items():
        row = {cat: val * fator for cat, val in cats.items() if val}
        if row:
            out[mes] = row
    return out


def _slug_categoria(categoria: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (categoria or CATEGORIA_OBRAS).lower()).strip("-")
    return (slug or "obras")[:40]


def source_id_trk_eng(building_id: str, mes: str, categoria: str) -> str:
    return f"{TRK_ENG_PREFIX}{building_id}-{mes}-{_slug_categoria(categoria)}"


def comprometido_obra_do_grupo(db: Session, cc_ids: list[int]) -> float:
    """Pago (recorte do orçamento) + contas a pagar em aberto. Não conta TRK-ENG."""
    ids = list({cid for cid in cc_ids if cid is not None})
    if not ids:
        return 0.0
    real = db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id.in_(ids),
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast.is_(False),
        or_(*[ActualTransaction.source_id.like(p) for p in SOURCE_ID_LIKES_REALIZADO_DESPESA]),
    ).all()
    aberto = db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id.in_(ids),
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast.is_(True),
        or_(
            ActualTransaction.source_id.like("FCST-OUT-%"),
            ActualTransaction.source_id.like("TRK-VENC-OUT-%"),
        ),
    ).all()
    return abs(sum(float(r.value or 0) for r in real)) + abs(sum(float(r.value or 0) for r in aberto))


def persistir_cronograma_engenharia(
    db: Session,
    building_id: str,
    target_cc_id: int,
    alocado: dict[str, dict[str, float]],
) -> int:
    """Substitui só TRK-ENG desse building. OP1 e FCST-OUT não são tocados."""
    db.query(ActualTransaction).filter(
        ActualTransaction.source_id.like(f"{TRK_ENG_PREFIX}{building_id}-%"),
    ).delete(synchronize_session=False)
    db.flush()
    count = 0
    for mes, cats in sorted(alocado.items()):
        try:
            ano_s, mes_s = mes.split("-")
            dtx = date(int(ano_s), int(mes_s), 1)
        except Exception:
            continue
        for categoria, valor in cats.items():
            amount = float(valor or 0)
            if amount <= 0:
                continue
            db.add(ActualTransaction(
                cost_center_id=target_cc_id,
                source_id=source_id_trk_eng(building_id, mes, categoria),
                transaction_type="OUTCOME",
                transaction_date=dtx,
                value=amount,
                category=categoria,
                is_forecast=True,
                document_name="Cronograma engenharia Sienge",
            ))
            count += 1
    db.commit()
    return count


def _tarefas_da_planilha(client, v1: str, building_id: str, sheet_id: Any) -> list[dict]:
    tarefas: list[dict] = []
    offset = 0
    while True:
        data = client.get_json(
            f"{v1}/building-projects/{building_id}/sheets/{sheet_id}/tasks?limit=200&offset={offset}",
            timeout=45,
            not_found_ok=True,
        ) or {}
        inner = data.get("results") or []
        if not inner:
            break
        tarefas.extend(inner)
        meta = data.get("resultSetMetadata") or {}
        if offset + len(inner) >= int(meta.get("count") or 0) or len(inner) < 200:
            break
        offset += 200
    return tarefas


def buscar_cronograma_engenharia(building_id: str, client=None) -> dict[str, dict[str, float]]:
    """Meses YYYY-MM → categoria → R$ (folha × % previsto). Ignora tarefas-resumo."""
    client = client or get_default_client()
    v1 = api_v1_base_url()
    sheets_data = client.get_json(
        f"{v1}/building-cost-estimations/{building_id}/sheets?limit=50&offset=0",
        timeout=45,
        not_found_ok=True,
    ) or {}
    sheets = list(sheets_data.get("results") or [])
    if not sheets:
        return {}
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for sheet in sheets:
        uid = sheet.get("id")
        if uid is None:
            continue
        categoria = categoria_do_sheet(sheet.get("description"))
        for task in _tarefas_da_planilha(client, v1, building_id, uid):
            if task.get("summary"):
                continue
            price = float(task.get("totalPrice") or 0)
            if price == 0:
                continue
            for pe in task.get("plannedExecutions") or []:
                pct = float(pe.get("plannedPercentage") or 0) / 100.0
                if pct == 0:
                    continue
                year = int(pe.get("year") or 0)
                month = int(pe.get("month") or 0)
                if year and 1 <= month <= 12:
                    monthly[f"{year:04d}-{month:02d}"][categoria] += price * pct
    return {mes: dict(cats) for mes, cats in monthly.items() if cats}


def resolver_building_id(client, membros: list[CostCenter]) -> Optional[str]:
    candidatos: list[str] = []
    prefixes = {m.id_sienge[:3] for m in membros if m.id_sienge and len(m.id_sienge) >= 3}
    for prefix in sorted(prefixes):
        candidatos.append(f"{prefix}00")
    for m in membros:
        if m.id_sienge and m.id_sienge not in candidatos:
            candidatos.append(m.id_sienge)
    v1 = api_v1_base_url()
    for bid in candidatos:
        data = client.get_json(
            f"{v1}/building-cost-estimations/{bid}/sheets?limit=1&offset=0",
            timeout=30,
            not_found_ok=True,
        ) or {}
        if data.get("results"):
            return bid
    return None


def _cc_alvo_do_grupo(membros: list[CostCenter], building_id: str) -> Optional[CostCenter]:
    obras = [m for m in membros if " - OBRAS" in (m.nome or "").upper()]
    if obras:
        return sorted(obras, key=lambda x: x.id_sienge or "")[0]
    building = [m for m in membros if m.id_sienge == building_id]
    if building:
        return building[0]
    if membros:
        return sorted(membros, key=lambda x: len(x.nome or ""))[0]
    return None


def _membros_do_produto(db: Session, cc: CostCenter) -> list[CostCenter]:
    from app.api.routes.tracking import _mesmo_produto_obra, parse_project_name

    if not cc.id_sienge or len(cc.id_sienge) < 3:
        return [cc]
    prefix = cc.id_sienge[:3]
    _, produto = parse_project_name(cc)
    related = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{prefix}%")).all()
    members = [rc for rc in related if _mesmo_produto_obra(produto, parse_project_name(rc)[1])]
    if not any(rc.id == cc.id for rc in members):
        members.append(cc)
    return members


def _fase_encerrada(cc: CostCenter) -> bool:
    return (cc.project_phase or "") in ("Encerrado", "Concluído")


def _gravar_building(db: Session, building_id: str, membros: list[CostCenter], client) -> int:
    alvo = _cc_alvo_do_grupo(membros, building_id)
    if not alvo:
        return 0
    cronograma = buscar_cronograma_engenharia(building_id, client=client)
    if not cronograma:
        persistir_cronograma_engenharia(db, building_id, alvo.id, {})
        return 0
    comprometido = comprometido_obra_do_grupo(db, [m.id for m in membros])
    alocado = alocar_cronograma_nao_comprometido(
        cronograma, comprometido, proximo_mes_yyyy_mm()
    )
    n = persistir_cronograma_engenharia(db, building_id, alvo.id, alocado)
    logger.info(
        "TRK-ENG building %s cc %s linhas %s comprometido %.2f",
        building_id, alvo.id_sienge, n, comprometido,
    )
    return n


def sync_engineering_disbursement_for_cc(db: Session, cc: CostCenter, client=None) -> int:
    """Um building por produto. No-op se a obra está encerrada ou a API não tem planilha."""
    if not cc.id_sienge or _fase_encerrada(cc):
        return 0
    client = client or get_default_client()
    membros = _membros_do_produto(db, cc)
    building_id = resolver_building_id(client, membros)
    if not building_id:
        return 0
    return _gravar_building(db, building_id, membros, client)


def sync_engineering_disbursements(db: Session, client=None) -> dict[str, int]:
    """Obras em andamento rastreadas. Um cronograma por buildingId."""
    client = client or get_default_client()
    tracked = db.query(CostCenter).filter(CostCenter.track_in_dashboard.is_(True)).all()
    done: set[str] = set()
    result: dict[str, int] = {}
    for cc in tracked:
        if _fase_encerrada(cc) or not cc.id_sienge:
            continue
        membros = _membros_do_produto(db, cc)
        building_id = resolver_building_id(client, membros)
        if not building_id or building_id in done:
            continue
        done.add(building_id)
        result[building_id] = _gravar_building(db, building_id, membros, client)
    return result
