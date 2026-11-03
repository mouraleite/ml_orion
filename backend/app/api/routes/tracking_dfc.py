"""DFC da vida do empreendimento — mesmo caixa do acompanhamento, visão DFC-padrão.

Não lê orçamento/forecast. Ano ou mês, grupos da visão, planos financeiros e conferência do lucro.
"""
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.api.routes.tracking import (
    _calc_actuals_for_cc,
    _mesmo_produto_obra,
    _prefetch_tracking_actuals,
    parse_project_name,
)
from app.db.database import get_db
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.vision import FinancialPlanVisionLink, Vision
from app.schemas.user import UserResponse

router = APIRouter()


def _grupos_cc_rastreaveis(db):
    """Mesmo agrupamento da lista: prefixo Sienge + produto, 100% da obra."""
    tracked = db.query(CostCenter).filter(CostCenter.track_in_dashboard == True).all()
    groups = {}
    for c in tracked:
        macro_prefix = c.id_sienge[:3] if c.id_sienge and len(c.id_sienge) >= 3 else str(c.id)
        city, proj_name = parse_project_name(c)
        group_key = f"{macro_prefix}_{proj_name}"
        if group_key in groups:
            continue
        members = []
        if c.id_sienge and len(c.id_sienge) >= 3:
            related = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{macro_prefix}%")).all()
            for rc in related:
                if _mesmo_produto_obra(proj_name, parse_project_name(rc)[1]):
                    members.append(rc)
        if not any(rc.id == c.id for rc in members):
            members.append(c)
        groups[group_key] = members
    return groups


def _item_empreendimento(group_key, members):
    main_cc = sorted(members, key=lambda x: len(x.nome or ""))[0]
    city, project_name = parse_project_name(main_cc)
    cat = "Encerrado" if main_cc.project_phase in ["Encerrado", "Concluído"] else "Em Andamento"
    return {
        "id": f"cg-{group_key}",
        "project_name": project_name,
        "city": city,
        "status": main_cc.project_phase or "Em Andamento",
        "category": cat,
        "centros": [
            {
                "id": cc.id,
                "id_sienge": cc.id_sienge,
                "nome": cc.nome,
            }
            for cc in sorted(members, key=lambda x: x.id_sienge or str(x.id))
        ],
    }


def listar_empreendimentos_dfc(db):
    groups = _grupos_cc_rastreaveis(db)
    items = [_item_empreendimento(key, members) for key, members in groups.items() if members]
    items.sort(key=lambda row: ((row.get("city") or ""), (row.get("project_name") or "")))
    return items


def _visao_e_mapas(db):
    vision = db.query(Vision).options(joinedload(Vision.nodes)).filter_by(is_padrao=True).first()
    if not vision:
        vision = db.query(Vision).options(joinedload(Vision.nodes)).first()
    nodes = sorted(
        [n for n in (vision.nodes if vision else []) if n.descricao],
        key=lambda n: ((n.codigo or ""), n.id or 0),
    )
    cat_to_group = {}
    cat_to_node_id = {}
    cat_to_fp = {}
    node_by_desc = {}
    for n in nodes:
        desc = (n.descricao or "").strip().upper()
        if desc:
            node_by_desc[desc] = n.id
    if nodes:
        node_map = {n.id: (n.descricao or "").strip().upper() for n in nodes}
        links = (
            db.query(FinancialPlanVisionLink, FinancialPlan)
            .join(FinancialPlan, FinancialPlan.id == FinancialPlanVisionLink.financial_plan_id)
            .filter(FinancialPlanVisionLink.vision_node_id.in_(node_map.keys()))
            .all()
        )
        for link, fp in links:
            if fp and fp.name:
                key = fp.name.strip().lower()
                cat_to_group[key] = node_map[link.vision_node_id]
                cat_to_node_id[key] = link.vision_node_id
                cat_to_fp[key] = {
                    "id": fp.id,
                    "codigo": fp.db_id or "",
                    "descricao": fp.name,
                }
    return vision, nodes, cat_to_group, cat_to_node_id, node_by_desc, cat_to_fp


def _node_id_codigo(nodes, codigo):
    for n in nodes:
        if (n.codigo or "") == codigo:
            return n.id
    return None


def _node_id_prefixo(nodes, prefixo):
    for n in sorted(nodes, key=lambda x: (x.codigo or "", x.id or 0)):
        if (n.codigo or "").startswith(prefixo):
            return n.id
    return None


# Planos que o DFC Sienge traz e a visão padrão ainda não vincula.
# Só o DFC de empreendimentos usa isso — não grava visão nem mexe no orçamento.
_PLANO_CODIGO_FALLBACK = {
    "irpj": "02.02",
    "csll": "02.02",
    "despesas de administração de empreendimentos": "04.04",
    "donativos e contribuições": "05.07",
}
_NOS_SIENGE_AUSENTES = (
    ("02.02", "IMPOSTOS TRIMESTRAIS"),
    ("04.04", "CUSTO ADM DE EMPREENDIMENTOS"),
    ("05.07", "DONATIVOS E CONTRIBUIÇÕES"),
)
_FORMULA_DFC = (
    ("03", ("04", "05")),
    ("06", ("01", "02", "03")),
    ("08", ("06", "07")),
    ("10", ("08", "09")),
    ("12", ("10", "11")),
)


def _garantir_nos_sienge(nodes):
    have = {(n.codigo or "").strip() for n in nodes}
    extra = list(nodes)
    next_id = -9000
    for codigo, descricao in _NOS_SIENGE_AUSENTES:
        if codigo in have:
            continue
        extra.append(SimpleNamespace(id=next_id, codigo=codigo, descricao=descricao))
        next_id -= 1
    extra.sort(key=lambda n: ((n.codigo or ""), n.id or 0))
    return extra


def _aplicar_fallback_planos(nodes, cat_to_group, cat_to_node_id):
    for nome, codigo in _PLANO_CODIGO_FALLBACK.items():
        if nome in cat_to_node_id:
            continue
        nid = _node_id_codigo(nodes, codigo)
        if not nid:
            continue
        cat_to_node_id[nome] = nid
        node = next((n for n in nodes if n.id == nid), None)
        if node:
            cat_to_group[nome] = (node.descricao or "").strip().upper()


def _signed_caixa_dfc(transaction_type, category, total_value):
    """Sienge DFC: entrada +, saída -. Redutora '(-) Retenção' entra positiva."""
    val = abs(float(total_value or 0.0))
    if transaction_type == "INCOME":
        return val
    nome = (category or "").strip()
    if nome.startswith("(-)"):
        return val
    return -val


def _eh_distrato(category, group):
    cat = (category or "").lower()
    grp = (group or "").upper()
    return "DISTRATO" in grp or "CANCELAMENTO" in grp or "distrat" in cat


def _destino_node(transaction_type, category, cat_to_group, cat_to_node_id, node_by_desc, node_venda_id, node_admin_id, node_cancel_id=None):
    cat = (category or "").lower().strip()
    group = cat_to_group.get(cat, "")
    if transaction_type == "INCOME":
        return cat_to_node_id.get(cat) or node_by_desc.get(group) or node_venda_id
    if transaction_type == "OUTCOME":
        if _eh_distrato(category, group):
            return cat_to_node_id.get(cat) or node_cancel_id or node_by_desc.get("CANCELAMENTOS DE VENDAS")
        return cat_to_node_id.get(cat) or node_by_desc.get(group) or node_admin_id
    return None


def _somar_nos(linhas, dest_codigo, origens):
    dest = next((row for row in linhas if (row.get("codigo") or "") == dest_codigo), None)
    if not dest:
        return
    meses = dict(dest.get("valores_mes") or {})
    for orig in origens:
        src = next((row for row in linhas if (row.get("codigo") or "") == orig), None)
        if not src:
            continue
        for mes, valor in (src.get("valores_mes") or {}).items():
            meses[mes] = meses.get(mes, 0.0) + valor
    dest["valores_mes"] = meses
    dest.update(_linha_valores(meses))


def _anos_de_meses(valores_mes):
    anos = defaultdict(float)
    for mes, valor in (valores_mes or {}).items():
        if mes and len(mes) >= 4:
            anos[mes[:4]] += valor
    return dict(anos)


def _linha_valores(valores_mes):
    meses = dict(valores_mes or {})
    anos = _anos_de_meses(meses)
    return {
        "valores": anos,
        "valores_mes": meses,
        "total": sum(meses.values()),
    }


def _pai_por_codigo(linhas, child_codigo):
    parent = None
    best = -1
    for cand in linhas:
        codigo = cand["codigo"] or ""
        if not codigo or codigo == child_codigo:
            continue
        if child_codigo.startswith(codigo + ".") and len(codigo) > best:
            parent = cand
            best = len(codigo)
    return parent


def montar_dfc_vida(db, group_id: str):
    group_key = group_id[3:] if group_id.startswith("cg-") else group_id
    groups = _grupos_cc_rastreaveis(db)
    members = groups.get(group_key)
    if not members:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado no acompanhamento.")

    vision, nodes, cat_to_group, cat_to_node_id, node_by_desc, cat_to_fp = _visao_e_mapas(db)
    if not vision or not nodes:
        raise HTTPException(status_code=404, detail="Visão DFC padrão não encontrada.")

    nodes = _garantir_nos_sienge(nodes)
    _aplicar_fallback_planos(nodes, cat_to_group, cat_to_node_id)
    for n in nodes:
        desc = (n.descricao or "").strip().upper()
        if desc and n.id not in node_by_desc.values():
            node_by_desc[desc] = n.id

    node_venda_id = _node_id_codigo(nodes, "01.01") or _node_id_prefixo(nodes, "01.")
    node_admin_id = (
        _node_id_codigo(nodes, "05.03")
        or node_by_desc.get("ADMINISTRATIVAS")
        or _node_id_prefixo(nodes, "05.")
    )
    node_cancel_id = (
        _node_id_codigo(nodes, "01.04")
        or node_by_desc.get("CANCELAMENTOS DE VENDAS")
    )

    cc_ids = [cc.id for cc in members]
    prefetched = _prefetch_tracking_actuals(db, cc_ids, include_forecast=True)

    valores_mes_folha = defaultdict(lambda: defaultdict(float))
    planos_mes = defaultdict(lambda: defaultdict(float))
    planos_info = {}
    lucro_dfc = 0.0

    def lancar_plano(nid, plan_id, codigo, descricao, mes, signed):
        planos_mes[(nid, plan_id)][mes] += signed
        if (nid, plan_id) not in planos_info:
            planos_info[(nid, plan_id)] = {
                "id": plan_id,
                "codigo": codigo or "",
                "descricao": descricao or "Sem plano",
            }

    def acumular(transaction_type, category, total_value, raw_mes):
        nonlocal lucro_dfc
        mes = raw_mes if raw_mes else "N/A"
        if not mes or mes == "N/A" or len(mes) < 7:
            return
        nid = _destino_node(
            transaction_type, category, cat_to_group, cat_to_node_id, node_by_desc,
            node_venda_id, node_admin_id, node_cancel_id,
        )
        if not nid:
            return
        signed = _signed_caixa_dfc(transaction_type, category, total_value)
        valores_mes_folha[nid][mes] += signed
        if nid != node_cancel_id:
            lucro_dfc += signed
        cat_key = (category or "").lower().strip()
        fp = cat_to_fp.get(cat_key)
        if fp:
            lancar_plano(nid, fp["id"], fp["codigo"], fp["descricao"], mes, signed)
        else:
            nome = (category or "").strip() or "Sem plano"
            lancar_plano(nid, f"x:{cat_key or '_'}", "", nome, mes, signed)

    for cc in members:
        for row in (prefetched.get("real") or {}).get(cc.id, []):
            acumular(row.transaction_type, row.category, row.total_value, row.mes)
        for row in (prefetched.get("pmt_hist") or {}).get(cc.id, []):
            acumular("OUTCOME", row.category, row.total_value, row.mes)
        for row in (prefetched.get("fcst") or {}).get(cc.id, []):
            acumular(row.transaction_type, row.category, row.total_value, row.mes)

    node_terreno_id = (
        node_by_desc.get("REPASSES TERRENISTAS")
        or node_by_desc.get("AQUISIÇÃO DE NOVAS ÁREAS")
        or _node_id_codigo(nodes, "04.01")
        or _node_id_prefixo(nodes, "04.")
    )
    for cc in members:
        mlc = float(getattr(cc, "manual_land_cost", 0) or 0)
        if mlc <= 0 or not node_terreno_id:
            continue
        meses_cc = sorted(
            {
                row.mes
                for row in (prefetched.get("real") or {}).get(cc.id, [])
                if getattr(row, "mes", None) and row.mes != "N/A"
            }
        )
        first_m = meses_cc[0] if meses_cc else datetime.now().strftime("%Y-%m")
        if len(first_m) >= 7:
            valores_mes_folha[node_terreno_id][first_m] -= mlc
            lucro_dfc -= mlc
            lancar_plano(node_terreno_id, "x:terreno-manual", "", "Terreno (custo manual)", first_m, -mlc)

    acts = [
        _calc_actuals_for_cc(
            db, cc.id, cached_cat_to_group=cat_to_group, prefetched=prefetched, kpis_only=True
        )
        for cc in members
    ]
    lucro_lista = sum((act.get("lucro_liq_operacional") or 0.0) for act in acts)
    desvio = lucro_dfc - lucro_lista

    planos_por_node = defaultdict(list)
    for (nid, plan_id), meses_plano in planos_mes.items():
        info = planos_info.get((nid, plan_id), {"id": plan_id, "codigo": "", "descricao": "Sem plano"})
        planos_por_node[nid].append({
            "kind": "plano",
            **info,
            **_linha_valores(meses_plano),
        })
    for nid in planos_por_node:
        planos_por_node[nid].sort(key=lambda p: ((p.get("descricao") or ""), str(p.get("id") or "")))

    linhas = []
    for node in nodes:
        linhas.append({
            "kind": "categoria",
            "id": node.id,
            "codigo": node.codigo or "",
            "descricao": node.descricao or "",
            "nivel": (node.codigo or "").count("."),
            "planos": planos_por_node.get(node.id, []),
            **_linha_valores(valores_mes_folha.get(node.id)),
        })

    for child in sorted(linhas, key=lambda r: r["codigo"].count("."), reverse=True):
        parent = _pai_por_codigo(linhas, child["codigo"])
        if not parent:
            continue
        for mes, valor in child["valores_mes"].items():
            parent["valores_mes"][mes] = parent["valores_mes"].get(mes, 0.0) + valor
        parent.update(_linha_valores(parent["valores_mes"]))

    for dest, origens in _FORMULA_DFC:
        _somar_nos(linhas, dest, origens)

    anos = sorted({ano for row in linhas for ano, valor in row["valores"].items() if abs(valor) > 0.005})
    meses = sorted({mes for row in linhas for mes, valor in row["valores_mes"].items() if abs(valor) > 0.005})
    item = _item_empreendimento(group_key, members)
    return {
        "empreendimento": item,
        "visao": {"id": vision.id, "nome": vision.nome, "is_padrao": bool(vision.is_padrao)},
        "anos": anos,
        "meses": meses,
        "linhas": linhas,
        "conferencia": {
            "lucro_dfc": lucro_dfc,
            "lucro_lista": lucro_lista,
            "desvio": desvio,
            "ok": abs(desvio) < 1.0,
        },
    }


@router.get("/dfc/empreendimentos")
def get_tracking_dfc_empreendimentos(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user),
):
    return {"items": listar_empreendimentos_dfc(db)}


@router.get("/dfc")
def get_tracking_dfc(
    id: str = Query(..., description="id do grupo, no mesmo formato da lista (cg-prefixo_produto)"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user),
):
    return montar_dfc_vida(db, id)
