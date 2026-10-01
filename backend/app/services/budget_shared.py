"""
Helpers estruturais compartilhados entre orçamento e forecast.

Não unifica regras de negócio (total_anual, meses fechados, receitas injetadas).
Rotas permanecem responsáveis por persistência e validações específicas.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.roles import is_diretor_user
from app.models.company import Company
from app.models.cost_center import CostCenter
from app.models.departamento import Departamento
from app.models.financial_plan import FinancialPlan
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.payment_plan import PaymentPlan
from app.services.periodos import MESES_STR, soma_meses_obj
from app.services.sharepoint_departamento import (
    fix_forecasts_sharepoint_sem_departamento,
)

LOCK_SECONDS = 1800


def build_empresas_map(db: Session) -> dict[str, str]:
    """Mapa id Sienge (e fallback id interno) → nome exibível."""
    result: dict[str, str] = {}
    for e in db.query(Company).all():
        nome = e.nome_fantasia or e.razao_social or f"Empresa {e.id}"
        if e.id_sienge:
            result[str(e.id_sienge)] = nome
        result[str(e.id)] = nome
    return result


def build_opcoes_produtos(produtos: Sequence, empresas_map: dict[str, str]) -> list[dict]:
    opcoes = []
    for p in produtos:
        empresa_id = (
            str(p.custom_data.get("__id_empresa"))
            if p.custom_data and p.custom_data.get("__id_empresa")
            else ""
        )
        nome_empresa = empresas_map.get(
            empresa_id,
            str(p.custom_data.get("__nome_empresa"))
            if p.custom_data and p.custom_data.get("__nome_empresa")
            else "",
        )
        opcoes.append(
            {
                "id": p.id,
                "nome": p.nome,
                "id_sienge": p.id_sienge,
                "id_empresa": empresa_id,
                "nome_empresa": nome_empresa,
            }
        )
    return opcoes


def merge_opcoes_produtos(*listas: Sequence[dict] | None) -> list[dict]:
    """Une opções de produto por id, sem duplicar."""
    by_id: dict[Any, dict] = {}
    for lista in listas:
        if not lista:
            continue
        for p in lista:
            if not isinstance(p, dict):
                continue
            pid = p.get("id")
            if pid is not None:
                by_id[pid] = p
    return list(by_id.values())


def filter_itens_por_empresa_ids(
    itens: list[dict],
    opcoes_produtos: Sequence[dict],
    empresa_ids: Sequence[str] | None,
) -> list[dict]:
    """Recorta linhas pelo id_empresa do produto — mesmo critério da matriz de orçamento."""
    if not empresa_ids:
        return itens
    wanted = {str(e).strip() for e in empresa_ids if str(e).strip()}
    if not wanted:
        return itens
    allowed = {
        p["id"]
        for p in opcoes_produtos
        if str(p.get("id_empresa") or "") in wanted
    }
    return [i for i in itens if i.get("produto_id") in allowed]


def expand_empresa_filter_ids(db: Session, empresa_ids: Sequence[str] | None) -> list[str]:
    """Inclui id Sienge e id interno da mesma empresa, para o recorte achar o cadastro."""
    wanted = {str(e).strip() for e in (empresa_ids or []) if str(e).strip()}
    if not wanted:
        return []
    numeric = [int(x) for x in wanted if x.isdigit()]
    clauses = [Company.id_sienge.in_(list(wanted))]
    if numeric:
        clauses.append(Company.id.in_(numeric))
    from sqlalchemy import or_
    for c in db.query(Company).filter(or_(*clauses)).all():
        if c.id_sienge:
            wanted.add(str(c.id_sienge))
        wanted.add(str(c.id))
    return list(wanted)


def build_opcoes_planos(planos: Sequence, *, nome_attr: str = "name") -> list[dict]:
    return [
        {"id": p.id, "nome": getattr(p, nome_attr), "db_id": getattr(p, "db_id", None)}
        for p in planos
    ]


def resolve_orcamento_monthly_catalog(
    db: Session,
    dept: Departamento,
    consolidado: bool,
    current_user,
    db_id_prefix: str,
) -> Tuple[list, list, bool]:
    """Catálogo permitido para GET despesas/receitas do orçamento."""
    from app.services.departamento_leitura import planos_ids_leitura, produtos_ids_leitura

    _ = consolidado
    is_consolidado = False
    tp = "D" if db_id_prefix == "2" else "R" if db_id_prefix == "1" else None
    plano_ids = planos_ids_leitura(db, dept, tp)
    if plano_ids:
        planos_permitidos = db.query(FinancialPlan).filter(FinancialPlan.id.in_(plano_ids)).all()
    else:
        planos_permitidos = []

    produtos_ids = produtos_ids_leitura(db, dept)
    if produtos_ids:
        produtos_permitidos = db.query(CostCenter).filter(CostCenter.id.in_(produtos_ids)).all()
    else:
        produtos_permitidos = []

    return planos_permitidos, produtos_permitidos, is_consolidado


def resolve_forecast_despesas_catalog(
    db: Session,
    dept: Departamento,
    consolidado: bool,
    current_user,
) -> Tuple[list, list, bool]:
    """Catálogo permitido para GET despesas do forecast."""
    from app.services.departamento_leitura import planos_ids_leitura, produtos_ids_leitura

    _ = consolidado
    is_consolidado = False
    plano_ids = planos_ids_leitura(db, dept, "D")
    planos_permitidos = (
        db.query(FinancialPlan).filter(FinancialPlan.id.in_(plano_ids)).all()
        if plano_ids
        else []
    )
    produtos_ids = produtos_ids_leitura(db, dept)
    produtos_permitidos = (
        db.query(CostCenter).filter(CostCenter.id.in_(produtos_ids)).all()
        if produtos_ids
        else []
    )
    return planos_permitidos, produtos_permitidos, is_consolidado


def merge_catalog_with_used_items(
    db: Session,
    produtos_permitidos: list,
    planos_permitidos: list,
    itens_db: Sequence,
) -> Tuple[list, list]:
    """Inclui produtos/planos já usados na grade (forecast despesas)."""
    prod_ids_used = [item.produto_id for item in itens_db]
    plan_ids_used = [item.plano_financeiro_id for item in itens_db]
    produtos_extras = (
        db.query(CostCenter).filter(CostCenter.id.in_(prod_ids_used)).all() if prod_ids_used else []
    )
    planos_extras = (
        db.query(FinancialPlan).filter(FinancialPlan.id.in_(plan_ids_used)).all()
        if plan_ids_used
        else []
    )

    produtos_dict = {p.id: p for p in produtos_permitidos}
    for p in produtos_extras:
        produtos_dict[p.id] = p

    planos_dict = {p.id: p for p in planos_permitidos}
    for p in planos_extras:
        planos_dict[p.id] = p

    return list(produtos_dict.values()), list(planos_dict.values())


def serialize_monthly_item_row(item, *, include_id: bool = True) -> dict:
    row = {
        "produto_id": item.produto_id,
        "plano_financeiro_id": item.plano_financeiro_id,
        "jan": item.jan or 0.0,
        "fev": item.fev or 0.0,
        "mar": item.mar or 0.0,
        "abr": item.abr or 0.0,
        "mai": item.mai or 0.0,
        "jun": item.jun or 0.0,
        "jul": item.jul or 0.0,
        "ago": item.ago or 0.0,
        "set": item.set or 0.0,
        "out": item.out or 0.0,
        "nov": item.nov or 0.0,
        "dez": item.dez or 0.0,
        "total_anual": item.total_anual or 0.0,
        "observacao": item.observacao,
    }
    if include_id:
        row["id"] = item.id
    return row


def serialize_base_monthly_item(ib, *, zero_defaults: bool = False) -> dict:
    if zero_defaults:
        meses = {m: getattr(ib, m) or 0.0 for m in MESES_STR}
        total = ib.total_anual or 0.0
    else:
        meses = {m: getattr(ib, m) for m in MESES_STR}
        total = ib.total_anual
    return {
        "produto_id": ib.produto_id,
        "plano_financeiro_id": ib.plano_financeiro_id,
        **meses,
        "total_anual": total,
    }


def serialize_venda_base_item(ib, *, zero_defaults: bool = False) -> dict:
    if zero_defaults:
        return {
            "produto_id": ib.produto_id,
            "plano_venda_id": ib.plano_venda_id,
            "mes": ib.mes,
            "ticket_medio": ib.ticket_medio or 0.0,
            "numero_vendas": ib.numero_vendas or 0,
            "vgv": ib.vgv or 0.0,
            "origem_venda": getattr(ib, "origem_venda", None),
        }
    return {
        "produto_id": ib.produto_id,
        "plano_venda_id": ib.plano_venda_id,
        "mes": ib.mes,
        "ticket_medio": ib.ticket_medio,
        "numero_vendas": ib.numero_vendas,
        "vgv": ib.vgv,
        "origem_venda": getattr(ib, "origem_venda", None),
    }


def serialize_venda_mes(item) -> dict:
    return {
        "mes": item.mes,
        "ticket_medio": item.ticket_medio or 0.0,
        "numero_vendas": item.numero_vendas or 0,
        "vgv": item.vgv or 0.0,
        "origem_venda": getattr(item, "origem_venda", None),
    }


def is_venda_distrato(item) -> bool:
    return "Distrato" in str(item.observacao or "") or (
        item.numero_vendas is not None and item.numero_vendas < 0
    )


def _payment_plan_display_name(plano) -> str:
    if not plano:
        return ""
    return str(getattr(plano, "nome", None) or getattr(plano, "name", "") or "")


def _vendas_orc_dept_scope(dept_id: int, dept_sienge_id: int):
    """Mesmo escopo de dept. das telas de orçamento/forecast de vendas."""
    return (
        (Orcamento.departamento_id == dept_id)
        | (Orcamento.departamento_id.is_(None))
        | (Orcamento.departamento_id == dept_sienge_id)
    )


def _vendas_forecast_dept_scope_simple(dept_id: int, dept_sienge_id: int):
    return (
        (Forecast.departamento_id == dept_id)
        | (Forecast.departamento_id.is_(None))
        | (Forecast.departamento_id == dept_sienge_id)
    )


def _orcamentos_venda_com_itens(db: Session, orcamento_id: int) -> bool:
    return (
        db.query(OrcamentoVendaItem)
        .filter(OrcamentoVendaItem.orcamento_id == orcamento_id)
        .first()
        is not None
    )


def flatten_venda_db_rows_for_visualizacao(db: Session, linhas_venda: Sequence) -> list[dict]:
    """Linhas mensais (mes, vgv). Mesmo produto+plano+mês de vários departamentos soma."""
    agregados: dict[tuple, dict] = {}
    for item in linhas_venda:
        key = (
            item.produto_id,
            item.plano_venda_id,
            item.mes,
            is_venda_distrato(item),
        )
        bucket = agregados.get(key)
        if bucket is None:
            plano = db.query(PaymentPlan).filter(PaymentPlan.id == item.plano_venda_id).first()
            produto = db.query(CostCenter).filter(CostCenter.id == item.produto_id).first()
            bucket = {
                "produto_id": item.produto_id,
                "produto_nome": produto.nome if produto else str(item.produto_id),
                "plano_venda_id": item.plano_venda_id,
                "plano_venda_nome": _payment_plan_display_name(plano) or str(item.plano_venda_id),
                "mes": item.mes,
                "vgv": 0.0,
                "numero_vendas": 0,
                "is_distrato": is_venda_distrato(item),
            }
            agregados[key] = bucket
        bucket["vgv"] += float(getattr(item, "vgv", 0.0) or 0.0)
        bucket["numero_vendas"] += int(getattr(item, "numero_vendas", 0) or 0)
    itens: list[dict] = []
    for bucket in agregados.values():
        qtd = bucket["numero_vendas"]
        vgv = bucket["vgv"]
        bucket["ticket_medio"] = (vgv / qtd) if qtd else 0.0
        itens.append(bucket)
    return itens


def group_venda_items(itens_db: Sequence) -> list[dict]:
    linhas_dict: dict[tuple, dict] = {}
    for item in itens_db:
        key = (item.produto_id, item.plano_venda_id, is_venda_distrato(item))
        if key not in linhas_dict:
            linhas_dict[key] = {
                "produto_id": item.produto_id,
                "plano_venda_id": item.plano_venda_id,
                "observacao": item.observacao,
                "meses": [],
            }
        linhas_dict[key]["meses"].append(serialize_venda_mes(item))
    return list(linhas_dict.values())


def check_pessimistic_lock(
    entity,
    current_user_id: int,
    *,
    usuario_edicao_attr: str = "usuario_edicao",
    lock_user_label: str = "Usuário ID",
) -> Tuple[bool, Optional[str]]:
    """Trava pessimista de leitura (30 min). Preserva getattr legado do orçamento despesas."""
    is_locked_by_other = False
    usuario_edicao_nome = None
    usuario_edicao_id = getattr(entity, "usuario_edicao_id", None)
    data_inicio_edicao = getattr(entity, "data_inicio_edicao", None)
    if usuario_edicao_id and data_inicio_edicao:
        if (datetime.utcnow() - data_inicio_edicao).total_seconds() < LOCK_SECONDS:
            if usuario_edicao_id != current_user_id:
                is_locked_by_other = True
            edicao = getattr(entity, usuario_edicao_attr, None)
            if edicao is not None and hasattr(edicao, "nome"):
                usuario_edicao_nome = edicao.nome
            else:
                usuario_edicao_nome = f"{lock_user_label} {usuario_edicao_id}"
    return is_locked_by_other, usuario_edicao_nome


def resolve_dept_sienge_id(db: Session) -> int:
    """Id do Corporativo residual (nome legado Consolidado - Sienge)."""
    from app.services.corporativo import corporativo_id_or_neg

    return corporativo_id_or_neg(db)


def resolve_dept_comercial_id(db: Session) -> int:
    dept_comercial = db.query(Departamento).filter(Departamento.nome.ilike("%COMERCIAL%")).first()
    return dept_comercial.id if dept_comercial else -1


DESCRICAO_DOCUMENTO_ORCAMENTO = "Orçamento"
STATUS_ORCAMENTO_BLOQUEADO = ("Aprovado", "Fechado", "Em aprovação", "Solicitação Reabertura")


def pode_editar_orcamento_vendas(user, dept) -> bool:
    """Orçamento e leitura de Vendas: departamento Vendas ou administrador."""
    from app.core.roles import is_admin_user

    if is_admin_user(user):
        return True
    return str(getattr(dept, "nome", "") or "").strip().upper() == "VENDAS"


def orcamentos_da_versao_visualizacao(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
    identifier: str,
) -> list:
    """Documentos de orçamento cujo rótulo visível coincide (ex.: Carga Inicial e Orçamento)."""
    from app.services.departamento_leitura import criterio_departamento_id

    alvo = format_visualizacao_versao_label(identifier, kind="orcamento")
    dept_filter = criterio_departamento_id(Orcamento.departamento_id, db, dept_id)
    orcs = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo.upper(),
            Orcamento.status != "Substituído",
            dept_filter,
        )
        .all()
    )
    return [
        o
        for o in orcs
        if format_visualizacao_versao_label(o.descricao, kind="orcamento") == alvo
    ]


def _parse_forecast_rolling_left(descricao: str | None) -> int | None:
    """Extrai o mês realizado de descrições como 'Forecast - 6+6'."""
    if not descricao:
        return None
    match = re.search(r"(\d+)\+\d+", descricao)
    return int(match.group(1)) if match else None


def _dedupe_versoes_mensais(versoes: Iterable) -> list[dict]:
    """Preferir versões válidas sobre 'Importado Sienge' com a mesma descrição."""
    v_dict: dict[str, dict] = {}
    for v in versoes:
        entry = {
            "id": v.id,
            "descricao": v.descricao,
            "versao_numero": v.versao_numero,
            "status": v.status,
        }
        if v.descricao not in v_dict or v_dict[v.descricao]["status"] == "Importado Sienge":
            v_dict[v.descricao] = entry
    return list(v_dict.values())


def list_forecast_versoes_disponiveis(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
) -> list[dict]:
    """
    Versões de forecast disponíveis para seleção, respeitando o cadastro de cada tipo:
    - DESPESAS/RECEITAS: forecasts mensais (ForecastItem) do departamento ativo / Sienge
    - VENDAS: forecasts de venda (ForecastVendaItem), excluindo cópias espúrias da série D/R
    """
    tipo = tipo.upper()
    from app.services.departamento_leitura import criterio_departamento_id

    if tipo in ("DESPESAS", "RECEITAS"):
        rows = (
            db.query(Forecast)
            .filter(
                Forecast.ano == ano,
                Forecast.tipo == tipo,
                criterio_departamento_id(Forecast.departamento_id, db, dept_id),
                Forecast.itens_despesa.any(),
            )
            .order_by(Forecast.versao_numero.desc(), Forecast.id.desc())
            .all()
        )
        return _dedupe_versoes_mensais(rows)

    if tipo != "VENDAS":
        return []

    dept_scope = criterio_departamento_id(Forecast.departamento_id, db, dept_id)

    explicit_desc = {
        d
        for (d,) in db.query(Forecast.descricao)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo == "VENDAS",
            Forecast.itens_venda.any(),
            (Forecast.produto_id.isnot(None)) | (Forecast.departamento_id.isnot(None)),
            dept_scope,
        )
        .distinct()
        .all()
        if d
    }

    dr_desc = {
        d
        for (d,) in db.query(Forecast.descricao)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo.in_(("DESPESAS", "RECEITAS")),
            Forecast.itens_despesa.any(),
            criterio_departamento_id(Forecast.departamento_id, db, dept_id),
        )
        .distinct()
        .all()
        if d
    }
    dr_months = [_parse_forecast_rolling_left(d) for d in dr_desc]
    dr_min_month = min((m for m in dr_months if m is not None), default=None)

    candidatos = (
        db.query(Forecast)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo == "VENDAS",
            Forecast.itens_venda.any(),
            dept_scope,
        )
        .order_by(Forecast.versao_numero.desc(), Forecast.id.desc())
        .all()
    )

    seen: set[str] = set()
    accepted: list = []
    for forecast in candidatos:
        descricao = forecast.descricao
        if not descricao or descricao in seen:
            continue

        bulk_legacy = forecast.produto_id is None and forecast.departamento_id is None
        if descricao in explicit_desc:
            ok = True
        elif bulk_legacy and descricao in dr_desc:
            ok = False
        elif bulk_legacy and dr_min_month is not None:
            rolling_left = _parse_forecast_rolling_left(descricao)
            ok = not (rolling_left is not None and rolling_left < dr_min_month)
        else:
            ok = True

        if ok:
            seen.add(descricao)
            accepted.append(forecast)

    return dedupe_versoes_por_descricao(accepted)


_PRIMEIRA_VERSAO_RE = re.compile(r"1\s*[ªºa°]?\s*vers", re.IGNORECASE)
_ROLLING_FORECAST_RE = re.compile(r"(\d+)\s*\+\s*(\d+)")


def is_primeira_versao_planilha(descricao: str | None) -> bool:
    """A planilha de vendas grava o orçamento como '1ª versão' / '1º versão'."""
    d = (descricao or "").strip()
    if not d:
        return False
    return bool(_PRIMEIRA_VERSAO_RE.search(d))


def canonical_versao_vendas_planilha(versao: str) -> tuple[str, str]:
    """
    Normaliza a coluna 'Versao orcamento' da planilha de vendas.
    Mantém '1ª versão' no banco (já existente) e padroniza forecast para 'Forecast - X+Y'.
    """
    d = (versao or "").strip() or "1ª versão"
    if is_primeira_versao_planilha(d):
        return d, "orcamento"
    rolling = _ROLLING_FORECAST_RE.search(d)
    if rolling:
        return f"Forecast - {int(rolling.group(1))}+{int(rolling.group(2))}", "forecast"
    return d, "forecast"


def format_visualizacao_versao_label(descricao: str | None, *, kind: str) -> str:
    """Rótulo legível sem duplicar 'Orçamento' ou 'Forecast'."""
    d = (descricao or "").strip()
    if not d:
        return "Orçamento" if kind == "orcamento" else "Forecast"
    low = d.lower()
    rolling = _ROLLING_FORECAST_RE.search(d)
    if kind == "orcamento":
        if (
            is_primeira_versao_planilha(d)
            or low in ("orçamento", "orcamento", "orçamento base", "orcamento base")
            or "orçamento vendas" in low
            or "orcamento vendas" in low
            # Mesma base orçada da carga Sienge — um só rótulo no comparativo
            or "carga inicial sienge" in low
        ):
            return "Orçamento"
        if low.startswith("orçamento") or low.startswith("orcamento"):
            return d
        return f"Orçamento — {d}"
    if rolling:
        return f"Forecast - {int(rolling.group(1))}+{int(rolling.group(2))}"
    if low.startswith("forecast"):
        return d
    return f"Forecast — {d}"


def _score_id_versao_para_dedupe(versao_id: str) -> int:
    low = (versao_id or "").lower()
    # Preferir a carga Sienge quando colide com o rótulo genérico "Orçamento"
    if "carga inicial" in low:
        return 3
    if "1ª" in versao_id or "1º" in versao_id or "vers" in low:
        return 2
    if "orçamento vendas" in low or "orcamento vendas" in low:
        return 0
    return 1


def _chave_ordem_versao(v: dict) -> tuple:
    vid = v.get("id") or ""
    desc = v.get("descricao") or ""
    rolling = _parse_forecast_rolling_left(desc) or _parse_forecast_rolling_left(vid)
    if vid.startswith("OC") or (not vid.startswith("FC") and rolling is None):
        return (0, desc.lower())
    return (1, rolling if rolling is not None else 99, desc.lower())


def ordenar_e_dedupar_labels_versao(versoes: list[dict]) -> list[dict]:
    """Uma opção por rótulo visível: Orçamento primeiro, depois Forecast 1+11 … 8+4."""
    by_label: dict[str, dict] = {}
    for v in versoes:
        label = v.get("descricao") or ""
        prev = by_label.get(label)
        if prev is None or _score_id_versao_para_dedupe(v.get("id") or "") > _score_id_versao_para_dedupe(prev.get("id") or ""):
            by_label[label] = v
    ordered = list(by_label.values())
    ordered.sort(key=_chave_ordem_versao)
    return ordered


def _filter_monthly_item_by_tipo(db: Session, item, tipo: str) -> bool:
    if tipo == "DESPESAS":
        prefix = "2"
    elif tipo == "RECEITAS":
        prefix = "1"
    else:
        return True
    plano = db.query(FinancialPlan).filter(FinancialPlan.id == item.plano_financeiro_id).first()
    if not plano:
        return False
    return str(plano.db_id or "").startswith(prefix)


def _monthly_orm_has_data(item) -> bool:
    if getattr(item, "observacao", None):
        return True
    return soma_meses_obj(item) != 0 or float(getattr(item, "total_anual", 0) or 0) != 0


def _monthly_row_has_data(row: dict) -> bool:
    if row.get("observacao"):
        return True
    return float(row.get("total", 0) or 0) != 0


def _venda_item_has_data(item) -> bool:
    """Vendas na visualização: considera preenchido quando há VGV (R$)."""
    return abs(float(getattr(item, "vgv", 0) or 0)) > 0.005


def _venda_orcamento_tem_dados_reais(db: Session, orcamento_id: int) -> bool:
    items = (
        db.query(OrcamentoVendaItem)
        .filter(OrcamentoVendaItem.orcamento_id == orcamento_id)
        .all()
    )
    return any(_venda_item_has_data(i) for i in items)


def _forecast_tem_dados_venda_reais(db: Session, forecast_id: int) -> bool:
    items = (
        db.query(ForecastVendaItem)
        .filter(ForecastVendaItem.forecast_id == forecast_id)
        .all()
    )
    return any(_venda_item_has_data(i) for i in items)


def _filtrar_itens_venda_com_dados(itens: list[dict]) -> list[dict]:
    """Mantém produto/plano só se houver VGV ou unidades em algum mês."""
    from collections import defaultdict

    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for item in itens:
        grupos[(item["produto_id"], item["plano_venda_id"])].append(item)

    filtrados: list[dict] = []
    for grupo in grupos.values():
        if any(abs(float(i.get("vgv") or 0)) > 0.005 for i in grupo):
            filtrados.extend(grupo)
    return filtrados


def _vendas_dept_scope(dept_id: int, dept_sienge_id: int, dept_comercial_id: int):
    """Escopo de departamento para orçamento/forecast de vendas (inclui Comercial e legado null)."""
    return (
        (Orcamento.departamento_id == dept_id)
        | (Orcamento.departamento_id == dept_sienge_id)
        | (Orcamento.departamento_id == dept_comercial_id)
        | (Orcamento.departamento_id.is_(None))
    )


def _vendas_forecast_dept_scope(dept_id: int, dept_sienge_id: int, dept_comercial_id: int):
    return (
        (Forecast.departamento_id == dept_id)
        | (Forecast.departamento_id.is_(None))
        | (Forecast.departamento_id == dept_sienge_id)
        | (Forecast.departamento_id == dept_comercial_id)
    )


def _plano_redutora(plano) -> bool:
    if not plano:
        return False
    return (
        str(getattr(plano, "fl_redutora", "") or "").strip().upper() == "S"
        or "reten" in str(getattr(plano, "name", "") or "").lower()
    )


def _plano_prefixo_tipo(plano, tipo: str) -> bool:
    tipo = (tipo or "").upper()
    if tipo == "DESPESAS":
        prefix = "2"
    elif tipo == "RECEITAS":
        prefix = "1"
    else:
        return True
    if not plano:
        return False
    return str(getattr(plano, "db_id", "") or "").startswith(prefix)


def assinar_itens_mensais_dfc(linhas, planos_por_id: dict, tipo: str) -> list[dict]:
    """Filtro de conta, sinal de redutora e soma por produto+plano.

    Mesma regra de extract_visualizacao_itens para despesas/receitas, sem
    carregar nome de produto nem consultar o banco por linha.
    """
    tipo = (tipo or "").upper()
    buckets: dict[tuple, dict] = {}
    for item in linhas or []:
        plano_id = getattr(item, "plano_financeiro_id", None)
        produto_id = getattr(item, "produto_id", None)
        plano = planos_por_id.get(plano_id)
        if not _plano_prefixo_tipo(plano, tipo):
            continue
        key = (produto_id, plano_id)
        redutora = _plano_redutora(plano)
        row = buckets.get(key)
        if row is None:
            row = {
                "produto_id": produto_id,
                "plano_financeiro_id": plano_id,
                **{m: 0.0 for m in MESES_STR},
                "total": 0.0,
            }
            buckets[key] = row
        for m in MESES_STR:
            val = float(getattr(item, m, 0) or 0)
            if redutora:
                val = -abs(val)
            row[m] += val
            row["total"] += val
    return list(buckets.values())


def _linhas_mensais_da_versao(db: Session, ano: int, tipo: str, dept_id: int, versao_id: str):
    """Itens de despesa/receita da versão, mesmo recorte de extract_visualizacao_itens."""
    tipo = tipo.upper()
    prefix = (versao_id or "").split("_")[0]
    identifier = "_".join((versao_id or "").split("_")[1:])
    is_orc = prefix in ("O", "OC")
    from app.services.departamento_leitura import criterio_departamento_id

    dept_filter_orc = criterio_departamento_id(Orcamento.departamento_id, db, dept_id)
    dept_filter_fc = criterio_departamento_id(Forecast.departamento_id, db, dept_id)
    linhas_db = []
    if is_orc:
        for o in orcamentos_da_versao_visualizacao(db, ano, tipo, dept_id, identifier):
            linhas_db.extend(
                db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == o.id).all()
            )
    else:
        fix_forecasts_sharepoint_sem_departamento(db)
        fcs = db.query(Forecast).filter(
            Forecast.ano == ano,
            Forecast.tipo == tipo,
            Forecast.descricao == identifier,
            dept_filter_fc,
        ).all()
        for f in fcs:
            linhas_db.extend(
                db.query(ForecastItem).filter(ForecastItem.forecast_id == f.id).all()
            )
    return linhas_db


def carregar_meses_dfc_comparativo(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
    versao_id: str,
) -> list[dict]:
    """Meses assinados do comparativo DFC: uma leitura dos itens e uma dos planos."""
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS"):
        return []
    linhas = _linhas_mensais_da_versao(db, ano, tipo, dept_id, versao_id)
    ids = {getattr(i, "plano_financeiro_id", None) for i in linhas}
    ids.discard(None)
    planos: dict = {}
    if ids:
        for plano in db.query(FinancialPlan).filter(FinancialPlan.id.in_(ids)).all():
            planos[plano.id] = plano
    return assinar_itens_mensais_dfc(linhas, planos, tipo)


def _enrich_monthly_visualizacao_row(db: Session, row: dict) -> dict:
    plano = db.query(FinancialPlan).filter(FinancialPlan.id == row["plano_financeiro_id"]).first()
    produto = db.query(CostCenter).filter(CostCenter.id == row["produto_id"]).first()
    is_redutora = False
    if plano:
        is_redutora = (
            str(getattr(plano, "fl_redutora", "") or "").strip().upper() == "S"
            or "reten" in str(plano.name or "").lower()
        )
    dados: dict[str, float] = {}
    total = 0.0
    for m in MESES_STR:
        val = float(row.get(m, 0) or 0)
        if is_redutora:
            val = -abs(val)
        dados[m] = val
        total += val
    return {
        "produto_id": row["produto_id"],
        "produto_nome": produto.nome if produto else str(row["produto_id"]),
        "plano_financeiro_id": row["plano_financeiro_id"],
        "plano_financeiro_nome": plano.name if plano else str(row.get("plano_financeiro_id", "")),
        **dados,
        "total": total,
        "observacao": row.get("observacao"),
    }


def _list_orcamento_descricoes_com_dados(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
) -> list[str]:
    tipo = tipo.upper()
    from app.services.departamento_leitura import criterio_departamento_id

    dept_filter = criterio_departamento_id(Orcamento.departamento_id, db, dept_id)

    orcs = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo,
            Orcamento.status != "Substituído",
            dept_filter,
        )
        .all()
    )
    descricoes: set[str] = set()
    for o in orcs:
        if not o.descricao:
            continue
        if tipo == "VENDAS":
            if _orcamentos_venda_com_itens(db, o.id):
                descricoes.add(o.descricao)
        else:
            descricoes.add(o.descricao)
    return sorted(descricoes)


def extract_visualizacao_itens(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
    versao_id: str,
) -> list[dict]:
    """Extrai linhas da matriz de visualização conforme tipo e versão (OC_/FC_)."""
    tipo = tipo.upper()
    prefix = versao_id.split("_")[0]
    identifier = "_".join(versao_id.split("_")[1:])
    is_orc = prefix in ("O", "OC")
    from app.services.departamento_leitura import criterio_departamento_id
    dept_filter_orc = criterio_departamento_id(Orcamento.departamento_id, db, dept_id)
    dept_filter_fc = criterio_departamento_id(Forecast.departamento_id, db, dept_id)

    if tipo in ("DESPESAS", "RECEITAS"):
        linhas_db = []
        if is_orc:
            for o in orcamentos_da_versao_visualizacao(db, ano, tipo, dept_id, identifier):
                linhas_db.extend(
                    db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == o.id).all()
                )
        else:
            fix_forecasts_sharepoint_sem_departamento(db)
            q = db.query(Forecast).filter(
                Forecast.ano == ano,
                Forecast.tipo == tipo,
                Forecast.descricao == identifier,
                dept_filter_fc,
            )
            fcs = q.all()
            for f in fcs:
                linhas_db.extend(
                    db.query(ForecastItem).filter(ForecastItem.forecast_id == f.id).all()
                )

        itens: list[dict] = []
        buckets: dict[tuple, dict] = {}
        for item in linhas_db:
            if not _filter_monthly_item_by_tipo(db, item, tipo):
                continue
            row = serialize_monthly_item_row(item, include_id=False)
            enriched = _enrich_monthly_visualizacao_row(db, row)
            key = (enriched["produto_id"], enriched["plano_financeiro_id"])
            prev = buckets.get(key)
            if prev is None:
                buckets[key] = enriched
                continue
            for m in MESES_STR:
                prev[m] += float(enriched.get(m, 0) or 0)
            prev["total"] += float(enriched.get("total", 0) or 0)
        itens = list(buckets.values())
        return itens

    linhas_venda = []
    if is_orc:
        for o in orcamentos_da_versao_visualizacao(db, ano, tipo, dept_id, identifier):
            linhas_venda.extend(
                db.query(OrcamentoVendaItem)
                .filter(OrcamentoVendaItem.orcamento_id == o.id)
                .all()
            )
    else:
        fix_forecasts_sharepoint_sem_departamento(db)
        fcs = (
            db.query(Forecast)
            .filter(
                Forecast.ano == ano,
                Forecast.tipo == "VENDAS",
                Forecast.descricao == identifier,
                dept_filter_fc,
            )
            .all()
        )
        for f in fcs:
            linhas_venda.extend(
                db.query(ForecastVendaItem)
                .filter(ForecastVendaItem.forecast_id == f.id)
                .all()
            )

    return flatten_venda_db_rows_for_visualizacao(db, linhas_venda)


def list_visualizacao_versoes_disponiveis(
    db: Session,
    ano: int,
    tipo: str,
    dept_id: int,
) -> list[dict]:
    """Orçamento base + forecasts filtrados (mesma regra do acompanhamento)."""
    tipo = tipo.upper()
    versoes: list[dict] = []

    for desc in _list_orcamento_descricoes_com_dados(db, ano, tipo, dept_id):
        versoes.append(
            {
                "id": f"OC_{desc}",
                "descricao": format_visualizacao_versao_label(desc, kind="orcamento"),
            }
        )

    for fc in list_forecast_versoes_disponiveis(db, ano, tipo, dept_id):
        desc = fc.get("descricao")
        if not desc:
            continue
        versoes.append(
            {
                "id": f"FC_{desc}",
                "descricao": format_visualizacao_versao_label(desc, kind="forecast"),
            }
        )

    return ordenar_e_dedupar_labels_versao(versoes)


def dedupe_versoes_por_descricao(versoes: Iterable) -> list[dict]:
    v_dict: dict[str, dict] = {}
    for v in versoes:
        if v.descricao not in v_dict:
            v_dict[v.descricao] = {
                "id": v.id,
                "descricao": v.descricao,
                "versao_numero": v.versao_numero,
                "status": v.status,
            }
    return list(v_dict.values())


def copy_monthly_items_to_forecast(
    itens_base: Sequence,
    forecast_id: int,
    forecast_item_cls,
) -> list:
    return [
        forecast_item_cls(
            forecast_id=forecast_id,
            produto_id=ib.produto_id,
            plano_financeiro_id=ib.plano_financeiro_id,
            jan=ib.jan,
            fev=ib.fev,
            mar=ib.mar,
            abr=ib.abr,
            mai=ib.mai,
            jun=ib.jun,
            jul=ib.jul,
            ago=ib.ago,
            set=ib.set,
            out=ib.out,
            nov=ib.nov,
            dez=ib.dez,
            total_anual=ib.total_anual,
            observacao=ib.observacao,
        )
        for ib in itens_base
    ]


def copy_venda_items_to_forecast(
    itens_base: Sequence,
    forecast_id: int,
    forecast_venda_cls,
) -> list:
    return [
        forecast_venda_cls(
            forecast_id=forecast_id,
            produto_id=ib.produto_id,
            plano_venda_id=ib.plano_venda_id,
            mes=ib.mes,
            ano=ib.ano,
            juros_mensal=ib.juros_mensal,
            ticket_medio=ib.ticket_medio,
            numero_vendas=ib.numero_vendas,
            vgv=ib.vgv,
            observacao=ib.observacao,
        )
        for ib in itens_base
    ]
