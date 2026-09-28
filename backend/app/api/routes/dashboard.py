from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api import deps
from app.models.user import User
from app.models.snapshot import PhaseSnapshot
from app.models.phase import Phase
from app.models.viability import Viability
from app.models.departamento import Departamento
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.vision import Vision, VisionNode
from app.api.deps import get_db, get_current_user, get_active_department
from app.core.roles import is_gestor_user
from app.models.forecast import Forecast
from app.services.orcamento_dfc import montar_dfc, montar_dfc_comparativo, par_ids_forecast_dfc
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.services.budget_shared import (
    merge_opcoes_produtos,
    filter_itens_por_empresa_ids,
    expand_empresa_filter_ids,
    list_forecast_versoes_disponiveis,
    list_visualizacao_versoes_disponiveis,
    ordenar_e_dedupar_labels_versao,
    carregar_meses_dfc_comparativo,
    build_empresas_map,
    build_opcoes_produtos,
)
from app.services.calculations import (
    agregar_serie_vendas_liquido,
    calcular_ranking_desvios,
    calculo_variacao_perc,
    calculo_variacao_rs,
    sumarizar_serie_mensal,
)
from app.api.routes.acompanhamento import (
    get_acompanhamento_despesas,
    get_acompanhamento_receitas,
    get_acompanhamento_vendas,
    MESES_STR
)
from app.services.realizado_sienge import (
    FONTE_REALIZADO_DESPESAS,
    build_planos_maps,
    query_parcelas_contas_pagar,
    valor_despesa_sienge,
)

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # 1. Obter todos os projetos e suas fases
    viabilities = db.query(Viability).all()
    
    total_vgv = 0.0
    total_projects = len(viabilities)
    total_lucro_liquido = 0.0
    
    # Vetores de caixa consolidado (indexados pelo mês)
    consolidated_cashflow: Dict[str, float] = {}
    consolidated_receitas: Dict[str, float] = {}
    consolidated_obras: Dict[str, float] = {}
    
    project_breakdown = []

    # 2. Iterar sobre todos os projetos e extrair o Baseline (Snapshot Oficial) de cada Fase
    for v in viabilities:
        proj_vgv = 0.0
        proj_lucro = 0.0
        proj_expo = 0.0
        proj_tir = 0.0
        proj_vpl = 0.0
        
        has_baseline = False
        
        for phase in v.phases:
            # Buscar o snapshot mais recente marcado como oficial para esta fase
            snapshot = db.query(PhaseSnapshot).filter(
                PhaseSnapshot.phase_id == phase.id,
                PhaseSnapshot.is_baseline == True
            ).order_by(desc(PhaseSnapshot.created_at)).first()
            
            if snapshot:
                has_baseline = True
                
                # Somar KPIs do projeto
                indicators = snapshot.indicators
                proj_vgv += indicators.get("vgv_total", 0.0)
                proj_lucro += indicators.get("lucro_liquido", 0.0)
                proj_vpl += indicators.get("vpl", 0.0)
                # A TIR não pode ser somada diretamente, mas para simplificação no breakdown listamos a do baseline.
                proj_tir = indicators.get("tir_aa", 0.0)
                # Exposição máxima (menor valor no fluxo). Como são valores negativos, podemos manter o menor ou somar as curvas.
                # A exposição consolidada real se dá pela soma dos fluxos de todos os projetos no tempo.
                
                # Consolidar Curvas de Tempo
                # No snapshot, temos cashflow_monthly como uma lista de dicts
                for item in snapshot.cashflow_monthly:
                    mes_idx = str(item.get("Mes", "0"))
                    
                    # Inicializar chaves se não existirem
                    if mes_idx not in consolidated_cashflow:
                        consolidated_cashflow[mes_idx] = 0.0
                        consolidated_receitas[mes_idx] = 0.0
                        consolidated_obras[mes_idx] = 0.0
                        
                    consolidated_cashflow[mes_idx] += item.get("Fluxo_de_Caixa", 0.0)
                    consolidated_receitas[mes_idx] += item.get("Receitas", 0.0)
                    consolidated_obras[mes_idx] += item.get("Obras", 0.0)
                    
        # Se o projeto teve pelo menos 1 fase com baseline oficial, entra nos totais da holding
        if has_baseline:
            total_vgv += proj_vgv
            total_lucro_liquido += proj_lucro
            
            project_breakdown.append({
                "id": v.id,
                "project_name": v.project_name,
                "status": v.status,
                "vgv": proj_vgv,
                "vpl": proj_vpl,
                "tir": proj_tir,
                "lucro_liquido": proj_lucro
            })

    # 3. Calcular Exposição Máxima Global baseado no fluxo de caixa consolidado de todos os projetos sobrepostos
    max_exposicao_global = 0.0
    caixa_acumulado_global = 0.0
    
    # Ordenar as chaves (meses) para calcular o acumulado
    sorted_months = sorted(consolidated_cashflow.keys(), key=lambda x: int(x) if x.isdigit() else 999)
    
    chart_data = []
    for mes in sorted_months:
        fluxo_mes = consolidated_cashflow[mes]
        caixa_acumulado_global += fluxo_mes
        if caixa_acumulado_global < max_exposicao_global:
            max_exposicao_global = caixa_acumulado_global
            
        chart_data.append({
            "name": f"Mês {mes}",
            "Receitas": consolidated_receitas[mes],
            "Obras": consolidated_obras[mes],
            "Fluxo_de_Caixa": fluxo_mes,
            "Acumulado": caixa_acumulado_global
        })

    # Blended global metrics
    global_margem = (total_lucro_liquido / total_vgv * 100) if total_vgv > 0 else 0.0

    return {
        "kpis": {
            "total_projects": len(project_breakdown), # Somente os que tem baseline
            "total_vgv": total_vgv,
            "total_lucro_liquido": total_lucro_liquido,
            "max_exposicao_global": max_exposicao_global,
            "global_margem": global_margem
        },
        "chart_data": chart_data,
        "project_breakdown": project_breakdown
    }


# ==================== DASHBOARD EXECUTIVO (Seção 24) ====================

MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


@router.get("/executivo/{ano}/forecasts")
def get_dashboard_forecasts(
    ano: int,
    consolidado: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    from app.models.forecast import Forecast
    query = db.query(Forecast).filter(Forecast.ano == ano, Forecast.status.in_(["Aprovado", "Fechado"]))
    if not consolidado and not is_gestor_user(current_user):
        from app.services.departamento_leitura import criterio_departamento
        query = query.filter(criterio_departamento(Forecast.departamento_id, db, dept))
    
    forecasts = query.order_by(desc(Forecast.id)).all()
    # Unique forecasts by ID, or we can just list them. Wait, there can be VENDAS and DESPESAS forecasts. 
    # For a consolidated view, we might just want to list distinct versao_numero or desc.
    # It's better to group by versao_numero or just return all with their type.
    result = []
    seen_desc = set()
    for f in forecasts:
        f_desc = f.descricao or f"Versão {f.versao_numero}"
        if f_desc not in seen_desc:
            seen_desc.add(f_desc)
            result.append({
                "id": f.id,
                "versao": f.versao_numero,
                "tipo": f.tipo,
                "descricao": f_desc,
                "data": f.data_criacao.strftime("%d/%m/%Y") if f.data_criacao else ""
            })
    return {"forecasts": result}


@router.get("/executivo/{ano}")
def get_dashboard_executivo(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    modo: str = "orcado",  # 'orcado' ou 'forecast'
    forecast_id: Optional[int] = None,
    meses: Optional[str] = None,
    empresa_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """
    Dashboard Executivo – Seção 24.
    Reutiliza internamente as funções de acompanhamento (Seção 22)
    para garantir consistência de valores com a tela Orçado × Realizado.
    """
    # ── 1. Buscar dados via camada de negócio (sem duplicar lógica) ──────
    desp_data = get_acompanhamento_despesas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=forecast_id)
    rec_data  = get_acompanhamento_receitas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=forecast_id)
    vend_data = get_acompanhamento_vendas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=forecast_id)

    desp_itens = desp_data.get("itens", [])
    rec_itens  = rec_data.get("itens", [])
    vend_itens = vend_data.get("itens", [])

    opcoes_produtos = merge_opcoes_produtos(
        desp_data.get("opcoes_produtos"),
        rec_data.get("opcoes_produtos"),
        vend_data.get("opcoes_produtos"),
    )
    ids_empresa = [e.strip() for e in empresa_ids.split(",")] if empresa_ids else []
    ids_empresa = expand_empresa_filter_ids(db, ids_empresa)
    if ids_empresa:
        desp_itens = filter_itens_por_empresa_ids(desp_itens, opcoes_produtos, ids_empresa)
        rec_itens = filter_itens_por_empresa_ids(rec_itens, opcoes_produtos, ids_empresa)
        vend_itens = filter_itens_por_empresa_ids(vend_itens, opcoes_produtos, ids_empresa)

    # ── 2. Série mensal (agregação) ───────────────────────────────────────
    serie_desp = sumarizar_serie_mensal(desp_itens, modo)
    serie_rec  = sumarizar_serie_mensal(rec_itens, modo)

    # Série de Vendas (VGV líquido, unidades) — estrutura aninhada vendas/distratos
    serie_vend_raw = agregar_serie_vendas_liquido(vend_itens)
    serie_vend = {
        "orcado":    {m: {"vgv": 0.0, "unidades": 0} for m in MESES_STR + ["total"]},
        "forecast":  {m: {"vgv": 0.0, "unidades": 0} for m in MESES_STR + ["total"]},
        "realizado": {m: {"vgv": 0.0, "unidades": 0} for m in MESES_STR + ["total"]},
    }
    for tp in ("orcado", "forecast", "realizado"):
        for m in MESES_STR:
            serie_vend[tp][m]["vgv"] = serie_vend_raw[tp][m]["vgv"]
            serie_vend[tp][m]["unidades"] = serie_vend_raw[tp][m]["unidades"]
        serie_vend[tp]["total"]["vgv"] = sum(serie_vend[tp][m]["vgv"] for m in MESES_STR)
        serie_vend[tp]["total"]["unidades"] = sum(serie_vend[tp][m]["unidades"] for m in MESES_STR)

    # Ticket médio global
    for tp in ["orcado", "forecast", "realizado"]:
        for m in MESES_STR + ["total"]:
            u = serie_vend[tp][m]["unidades"]
            v = serie_vend[tp][m]["vgv"]
            serie_vend[tp][m]["ticket_medio"] = (v / u) if u > 0 else 0.0

    # ── 3. KPI Cards ─────────────────────────────────────────────────────
    ref = modo  # 'orcado' ou 'forecast'

    meses_validos = [m.strip() for m in meses.split(",")] if meses else MESES_STR
    meses_validos = [m for m in meses_validos if m in MESES_STR]
    if not meses_validos:
        meses_validos = MESES_STR

    desp_ref  = sum(serie_desp[ref].get(m, 0.0) for m in meses_validos)
    desp_real = sum(serie_desp["realizado"].get(m, 0.0) for m in meses_validos)
    rec_ref   = sum(serie_rec[ref].get(m, 0.0) for m in meses_validos)
    rec_real  = sum(serie_rec["realizado"].get(m, 0.0) for m in meses_validos)

    resultado_ref  = rec_ref  - desp_ref
    resultado_real = rec_real - desp_real

    vgv_ref = sum(serie_vend[ref][m]["vgv"] for m in meses_validos)
    vgv_real = sum(serie_vend["realizado"][m]["vgv"] for m in meses_validos)
    unid_ref = sum(serie_vend[ref][m]["unidades"] for m in meses_validos)
    unid_real = sum(serie_vend["realizado"][m]["unidades"] for m in meses_validos)
    tk_ref = (vgv_ref / unid_ref) if unid_ref > 0 else 0.0
    tk_real = (vgv_real / unid_real) if unid_real > 0 else 0.0

    kpis = {
        # Despesas
        "desp_referencia": desp_ref,
        "desp_realizado":  desp_real,
        "desp_saldo":      calculo_variacao_rs(desp_real, desp_ref),
        "desp_desvio_perc": calculo_variacao_perc(desp_real, desp_ref),
        # Receitas
        "rec_referencia":  rec_ref,
        "rec_realizado":   rec_real,
        "rec_saldo":       calculo_variacao_rs(rec_real, rec_ref),
        "rec_desvio_perc": calculo_variacao_perc(rec_real, rec_ref),
        # Resultado líquido
        "resultado_referencia": resultado_ref,
        "resultado_realizado":  resultado_real,
        "resultado_saldo":      calculo_variacao_rs(resultado_real, resultado_ref),
        "resultado_desvio_perc": calculo_variacao_perc(resultado_real, resultado_ref),
        # Vendas
        "vgv_referencia":    vgv_ref,
        "vgv_realizado":     vgv_real,
        "vgv_desvio_perc":   calculo_variacao_perc(vgv_real, vgv_ref),
        "unidades_referencia": unid_ref,
        "unidades_realizado":  unid_real,
        "ticket_medio_realizado": tk_real,
        "ticket_medio_referencia": tk_ref,
    }

    # ── 4. Série mensal para gráficos ─────────────────────────────────────
    chart_mensal = []
    for i, mes in enumerate(MESES_STR):
        chart_mensal.append({
            "mes": MESES_LABEL[i],
            "desp_orcado":    serie_desp["orcado"][mes],
            "desp_forecast":  serie_desp["forecast"][mes],
            "desp_realizado": serie_desp["realizado"][mes],
            "rec_orcado":     serie_rec["orcado"][mes],
            "rec_forecast":   serie_rec["forecast"][mes],
            "rec_realizado":  serie_rec["realizado"][mes],
            "vgv_orcado":     serie_vend["orcado"][mes]["vgv"],
            "vgv_forecast":   serie_vend["forecast"][mes]["vgv"],
            "vgv_realizado":  serie_vend["realizado"][mes]["vgv"],
            "resultado_ref":  serie_rec[ref][mes] - serie_desp[ref][mes],
            "resultado_real": serie_rec["realizado"][mes] - serie_desp["realizado"][mes],
        })

    # ── 5. Ranking de maiores desvios ─────────────────────────────────────
    todos_itens = desp_itens + rec_itens
    
    # Atualizar "total" para refletir apenas os meses selecionados (afeta ranking e drill_down)
    for item in todos_itens:
        for tp in ["orcado", "forecast", "realizado"]:
            if tp in item and isinstance(item[tp], dict):
                item[tp]["total"] = sum((item[tp].get(m, 0.0) or 0.0) for m in meses_validos)

    ranking_raw = calcular_ranking_desvios(todos_itens, modo=modo, top_n=10)

    # Enriquecer com nomes
    prod_ids  = {r["produto_id"] for r in todos_itens if r.get("produto_id")}
    plano_ids = {r["plano_financeiro_id"] for r in todos_itens if r.get("plano_financeiro_id")}

    prod_map = (
        {p.id: p.nome for p in db.query(CostCenter).filter(CostCenter.id.in_(prod_ids)).all()}
        if prod_ids else {}
    )
    plano_map = (
        {p.id: p.name for p in db.query(FinancialPlan).filter(FinancialPlan.id.in_(plano_ids)).all()}
        if plano_ids else {}
    )

    desp_keys = {
        (r["produto_id"], r.get("plano_financeiro_id"))
        for r in desp_itens
    }

    ranking = []
    for r in ranking_raw:
        key = (r["produto_id"], r.get("plano_financeiro_id"))
        ranking.append({
            **r,
            "produto_nome": prod_map.get(r["produto_id"], str(r["produto_id"])),
            "plano_nome":   plano_map.get(r.get("plano_financeiro_id"), "-"),
            "tipo": "DESPESAS" if key in desp_keys else "RECEITAS",
        })

    # ── 6. Drill-down: Produto → Plano → Mês (despesas + receitas) ────────
    drill_down_map: Dict[int, Dict] = {}

    def enriquecer_drill(itens: list, categoria: str):
        for item in itens:
            pid = item.get("produto_id")
            plid = item.get("plano_financeiro_id") or item.get("plano_venda_id")
            if pid is None:
                continue
            if pid not in drill_down_map:
                drill_down_map[pid] = {
                    "produto_id": pid,
                    "produto_nome": prod_map.get(pid) or str(pid),
                    "planos": {},
                }
            plano_key = plid or 0
            if plano_key not in drill_down_map[pid]["planos"]:
                drill_down_map[pid]["planos"][plano_key] = {
                    "plano_id": plid,
                    "plano_nome": plano_map.get(plid, "-") if plid else "-",
                    "categoria": categoria,
                    "meses": {mes: {
                        ref: (item.get(ref, {}).get(mes, 0.0) or 0.0),
                        "realizado": (item.get("realizado", {}).get(mes, 0.0) or 0.0),
                    } for mes in MESES_STR + ["total"]},
                }

    enriquecer_drill(desp_itens, "DESPESAS")
    enriquecer_drill(rec_itens, "RECEITAS")

    drill_down = []
    for pid, pdata in drill_down_map.items():
        pdata["planos"] = list(pdata["planos"].values())
        drill_down.append(pdata)

    # ── 7. Metadata ──────────────────────────────────────────────────────
    response = {
        "ano": ano,
        "modo": modo,
        "is_consolidado": desp_data.get("is_consolidado", False),
        "meses_selecionados": meses_validos,
        "kpis": kpis,
        "chart_mensal": chart_mensal,
        "ranking_desvios": ranking,
        "drill_down": drill_down,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": desp_data.get("opcoes_planos", []),
    }
    if holding_mldu:
        avisos = list(
            dict.fromkeys(
                (desp_data.get("holding_avisos") or [])
                + (rec_data.get("holding_avisos") or [])
                + (vend_data.get("holding_avisos") or [])
            )
        )
        response["holding_mldu"] = True
        response["holding_avisos"] = avisos
    return response


def _visao_padrao_spec(db: Session) -> tuple[Optional[Vision], List[Dict]]:
    vision = db.query(Vision).filter_by(is_padrao=True).first()
    if not vision:
        vision = db.query(Vision).order_by(Vision.id.asc()).first()
    if not vision:
        return None, []
    nodes = (
        db.query(VisionNode)
        .filter(VisionNode.vision_id == vision.id)
        .order_by(VisionNode.codigo.asc())
        .all()
    )
    spec: List[Dict] = []
    for node in nodes:
        planos = []
        for link in node.plan_links:
            plano = link.financial_plan
            if not plano:
                continue
            planos.append({"id": plano.id, "name": plano.name, "db_id": plano.db_id})
        spec.append({
            "id": node.id,
            "codigo": node.codigo or "",
            "descricao": node.descricao or "",
            "planos": planos,
        })
    return vision, spec


def _ids_forecast_dfc(
    db: Session,
    forecast_id: Optional[int],
    ano: int,
    dept_id: int,
) -> tuple[Optional[int], Optional[int]]:
    """Par Despesas/Receitas da mesma descrição — o acompanhamento exige id do próprio tipo."""
    if not forecast_id:
        return None, None
    row = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    escolhido = None
    ano_ref = ano
    dept_ref = dept_id
    if row:
        escolhido = {
            "id": row.id,
            "tipo": row.tipo,
            "descricao": row.descricao,
            "departamento_id": row.departamento_id,
        }
        ano_ref = row.ano or ano
        dept_ref = row.departamento_id or dept_id
    pares = [
        {
            "id": f.id,
            "tipo": f.tipo,
            "descricao": f.descricao,
            "departamento_id": f.departamento_id,
        }
        for f in db.query(Forecast)
        .filter(Forecast.ano == ano_ref, Forecast.tipo.in_(("DESPESAS", "RECEITAS")))
        .all()
    ]
    return par_ids_forecast_dfc(forecast_id, escolhido, pares, dept_ref)


def _versoes_forecast_dfc(db: Session, ano: int, dept_id: int) -> List[Dict]:
    """Versões com itens mensais (Despesas, e Receitas se a descrição ainda não estiver na lista)."""
    versoes = list(list_forecast_versoes_disponiveis(db, ano, "DESPESAS", dept_id) or [])
    seen = {v.get("descricao") for v in versoes}
    for v in list_forecast_versoes_disponiveis(db, ano, "RECEITAS", dept_id) or []:
        if v.get("descricao") not in seen:
            versoes.append(v)
            seen.add(v.get("descricao"))
    return versoes


@router.get("/dfc/{ano}")
def get_orcamento_dfc(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    meses: Optional[str] = None,
    empresa_ids: Optional[str] = None,
    forecast_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """DFC do orçamento: mesma origem do Orçado × Realizado, agrupada pela Visão padrão."""
    vision, nodes_spec = _visao_padrao_spec(db)
    desp_id, rec_id = _ids_forecast_dfc(db, forecast_id, ano, dept.id)

    desp_n = get_acompanhamento_despesas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=desp_id)
    rec_n = get_acompanhamento_receitas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=rec_id)
    desp_n1 = get_acompanhamento_despesas(ano - 1, consolidado, holding_mldu, db, dept, current_user)
    rec_n1 = get_acompanhamento_receitas(ano - 1, consolidado, holding_mldu, db, dept, current_user)

    desp_itens = desp_n.get("itens", [])
    rec_itens = rec_n.get("itens", [])
    desp_itens_n1 = desp_n1.get("itens", [])
    rec_itens_n1 = rec_n1.get("itens", [])

    opcoes_produtos = merge_opcoes_produtos(
        desp_n.get("opcoes_produtos"),
        rec_n.get("opcoes_produtos"),
        desp_n1.get("opcoes_produtos"),
        rec_n1.get("opcoes_produtos"),
    )
    ids_empresa = [e.strip() for e in empresa_ids.split(",")] if empresa_ids else []
    ids_empresa = expand_empresa_filter_ids(db, ids_empresa)
    if ids_empresa:
        desp_itens = filter_itens_por_empresa_ids(desp_itens, opcoes_produtos, ids_empresa)
        rec_itens = filter_itens_por_empresa_ids(rec_itens, opcoes_produtos, ids_empresa)
        desp_itens_n1 = filter_itens_por_empresa_ids(desp_itens_n1, opcoes_produtos, ids_empresa)
        rec_itens_n1 = filter_itens_por_empresa_ids(rec_itens_n1, opcoes_produtos, ids_empresa)

    meses_validos = [m.strip() for m in meses.split(",")] if meses else MESES_STR
    meses_validos = [m for m in meses_validos if m in MESES_STR]
    if not meses_validos:
        meses_validos = list(MESES_STR)

    arvore = montar_dfc(
        nodes_spec,
        rec_itens,
        desp_itens,
        rec_itens_n1,
        desp_itens_n1,
        meses_validos,
    )

    response = {
        "ano": ano,
        "ano_anterior": ano - 1,
        "meses_selecionados": meses_validos,
        "visao": (
            {"id": vision.id, "nome": vision.nome, "is_padrao": bool(vision.is_padrao)}
            if vision
            else None
        ),
        "ah_base": "real_n1",
        "av_ancora": "total_entradas",
        "active_forecast_id": desp_id or rec_id or desp_n.get("active_forecast_id") or rec_n.get("active_forecast_id"),
        "versoes_disponiveis": _versoes_forecast_dfc(db, ano, dept.id),
        **arvore,
        "opcoes_produtos": opcoes_produtos,
    }
    if holding_mldu:
        avisos = list(
            dict.fromkeys(
                (desp_n.get("holding_avisos") or [])
                + (rec_n.get("holding_avisos") or [])
                + (desp_n1.get("holding_avisos") or [])
                + (rec_n1.get("holding_avisos") or [])
            )
        )
        response["holding_mldu"] = True
        response["holding_avisos"] = avisos
    return response


def _versoes_dfc_comparativo(db: Session, ano: int, dept_id: int) -> List[Dict]:
    """Mesmas opções do Comparativo consolidado (OC_/FC_), rótulo único Orçamento."""
    seen: Dict[str, Dict] = {}
    for t in ("DESPESAS", "RECEITAS"):
        for v in list_visualizacao_versoes_disponiveis(db, ano, t, dept_id):
            seen.setdefault(v["id"], v)
    return ordenar_e_dedupar_labels_versao(list(seen.values()))


@router.get("/dfc/{ano}/comparativo")
def get_orcamento_dfc_comparativo(
    ano: int,
    versao_a: str,
    versao_b: str,
    holding_mldu: bool = False,
    meses: Optional[str] = None,
    empresa_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """DFC lado a lado: duas versões (OC_/FC_) na Visão padrão — sem recalcular fórmulas."""
    _ = current_user
    vision, nodes_spec = _visao_padrao_spec(db)
    if not nodes_spec:
        return {
            "ano": ano,
            "modo": "comparativo",
            "visao": None,
            "versao_a": versao_a,
            "versao_b": versao_b,
            "linhas": [],
            "versoes_disponiveis": _versoes_dfc_comparativo(db, ano, dept.id),
            "message": "Nenhuma Visão DFC cadastrada.",
        }

    meses_validos = [m.strip() for m in meses.split(",")] if meses else list(MESES_STR)
    meses_validos = [m for m in meses_validos if m in MESES_STR] or list(MESES_STR)

    rec_a = carregar_meses_dfc_comparativo(db, ano, "RECEITAS", dept.id, versao_a)
    desp_a = carregar_meses_dfc_comparativo(db, ano, "DESPESAS", dept.id, versao_a)
    rec_b = carregar_meses_dfc_comparativo(db, ano, "RECEITAS", dept.id, versao_b)
    desp_b = carregar_meses_dfc_comparativo(db, ano, "DESPESAS", dept.id, versao_b)

    ids_empresa = [e.strip() for e in empresa_ids.split(",")] if empresa_ids else []
    ids_empresa = expand_empresa_filter_ids(db, ids_empresa)
    if ids_empresa:
        produtos = db.query(CostCenter).filter(CostCenter.status == "Ativo").all()
        empresas_map = build_empresas_map(db)
        opcoes = build_opcoes_produtos(produtos, empresas_map)
        rec_a = filter_itens_por_empresa_ids(rec_a, opcoes, ids_empresa)
        desp_a = filter_itens_por_empresa_ids(desp_a, opcoes, ids_empresa)
        rec_b = filter_itens_por_empresa_ids(rec_b, opcoes, ids_empresa)
        desp_b = filter_itens_por_empresa_ids(desp_b, opcoes, ids_empresa)

    holding_avisos: List[str] = []
    if holding_mldu:
        def _escala(itens: list) -> list:
            scaled = maybe_apply_holding_mldu(
                db, True, {"itens": itens}, item_kind="visualizacao_monthly",
            )
            holding_avisos.extend(scaled.get("holding_avisos") or [])
            return scaled.get("itens") or []

        rec_a, desp_a = _escala(rec_a), _escala(desp_a)
        rec_b, desp_b = _escala(rec_b), _escala(desp_b)

    arvore = montar_dfc_comparativo(nodes_spec, rec_a, desp_a, rec_b, desp_b, meses_validos)
    versoes = _versoes_dfc_comparativo(db, ano, dept.id)
    nome = {v["id"]: v.get("descricao") or v["id"] for v in versoes}

    return {
        "ano": ano,
        "modo": "comparativo",
        "meses_selecionados": meses_validos,
        "visao": (
            {"id": vision.id, "nome": vision.nome, "is_padrao": bool(vision.is_padrao)}
            if vision
            else None
        ),
        "versao_a": versao_a,
        "versao_b": versao_b,
        "label_a": nome.get(versao_a, versao_a),
        "label_b": nome.get(versao_b, versao_b),
        "versoes_disponiveis": versoes,
        "holding_mldu": bool(holding_mldu),
        "holding_avisos": list(dict.fromkeys(holding_avisos)),
        **arvore,
    }


# ==================== REALIZADO DESPESAS (Contas a Pagar — drill) ====================

def _serialize_parcelas_despesas(
    reais: list,
    db: Session,
    prod_map: Dict[int, str],
    plano_map: Dict[int, str],
    plano_id_filter: Optional[int] = None,
) -> List[Dict]:
    planos_id_map, planos_redutora = build_planos_maps(db)

    out: List[Dict] = []
    for real in reais:
        plid = planos_id_map.get(real.category)
        if not plid:
            continue
        if plano_id_filter is not None and plid != plano_id_filter:
            continue

        mes_str = MESES_STR[real.transaction_date.month - 1]
        val = valor_despesa_sienge(real.value, plid, real.category, planos_redutora)

        out.append({
            "id": real.id,
            "produto_id": real.cost_center_id,
            "produto_nome": prod_map.get(real.cost_center_id, str(real.cost_center_id)),
            "plano_id": plid,
            "plano_nome": plano_map.get(plid, real.category or "-"),
            "credor": real.creditor_name or "Sem credor",
            "documento_nome": real.document_name or "—",
            "documento_numero": real.document_number or "—",
            "titulo": real.bill_id or "—",
            "autorizacao": real.authorization_name or "—",
            "transaction_date": real.transaction_date.isoformat() if real.transaction_date else None,
            "mes": mes_str,
            "valor": val,
        })
    return out


@router.get("/realizado-despesas/{ano}")
def get_realizado_despesas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    produto_id: Optional[int] = None,
    plano_id: Optional[int] = None,
    mes: Optional[str] = None,
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """
    Ledger de parcelas pagas (Contas a Pagar — Sienge OUT-*).
    Usado no drill do Analítico I e na tela Realizado Detalhado.
    """
    desp_data = get_acompanhamento_despesas(
        ano, consolidado, holding_mldu, db, dept, current_user, forecast_id=None
    )
    produtos_permitidos = [p["id"] for p in desp_data.get("opcoes_produtos", [])]
    prod_map = {p["id"]: p["nome"] for p in desp_data.get("opcoes_produtos", [])}
    plano_map = {p["id"]: p["nome"] for p in desp_data.get("opcoes_planos", [])}

    if produto_id is not None and produto_id not in produtos_permitidos:
        produto_id = None

    reais = query_parcelas_contas_pagar(
        db, ano, produtos_permitidos, produto_id, mes, busca, dept=dept
    )
    transacoes = _serialize_parcelas_despesas(reais, db, prod_map, plano_map, plano_id)

    response: Dict[str, Any] = {
        "ano": ano,
        "is_consolidado": desp_data.get("is_consolidado", consolidado),
        "transacoes": transacoes,
        "total": sum(t["valor"] for t in transacoes),
        "opcoes_produtos": desp_data.get("opcoes_produtos", []),
        "opcoes_planos": desp_data.get("opcoes_planos", []),
        "fonte": FONTE_REALIZADO_DESPESAS,
    }
    if holding_mldu:
        response["holding_mldu"] = True
        response["holding_avisos"] = desp_data.get("holding_avisos") or []
    return response


# ==================== MATRIZ DETALHADA ====================

@router.get("/matriz-detalhada/{ano}")
def get_matriz_detalhada(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    forecast_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """
    Retorna a matriz detalhada com drill-down até parcelas pagas (Contas a Pagar).
    """
    desp_data = get_acompanhamento_despesas(
        ano, consolidado, holding_mldu, db, dept, current_user, forecast_id
    )
    desp_itens = desp_data.get("itens", [])
    produtos_permitidos = [p["id"] for p in desp_data.get("opcoes_produtos", [])]

    prod_map = {p["id"]: p["nome"] for p in desp_data.get("opcoes_produtos", [])}
    plano_map = {p["id"]: p["nome"] for p in desp_data.get("opcoes_planos", [])}

    planos_id_map, planos_redutora = build_planos_maps(db)

    detalhamento_map: Dict[tuple, Dict] = {}

    def init_detalhe(pid, plid):
        key = (pid, plid)
        if key not in detalhamento_map:
            detalhamento_map[key] = {
                "produto_id": pid,
                "produto_nome": prod_map.get(pid, str(pid)),
                "plano_id": plid,
                "plano_nome": plano_map.get(plid, "-"),
                "orcado": {m: 0.0 for m in MESES_STR + ["total"]},
                "forecast": {m: 0.0 for m in MESES_STR + ["total"]},
                "realizado": {m: 0.0 for m in MESES_STR + ["total"]},
                "transacoes": {},
            }
        return detalhamento_map[key]

    for item in desp_itens:
        pid = item.get("produto_id")
        plid = item.get("plano_financeiro_id")
        if not pid or not plid:
            continue
        node = init_detalhe(pid, plid)
        for tp in ["orcado", "forecast", "realizado"]:
            for m in MESES_STR + ["total"]:
                node[tp][m] += item.get(tp, {}).get(m, 0.0) or 0.0

    reais = query_parcelas_contas_pagar(db, ano, produtos_permitidos, dept=dept)

    for real in reais:
        plid = planos_id_map.get(real.category)
        if not plid:
            continue
        node = init_detalhe(real.cost_center_id, plid)
        mes_str = MESES_STR[real.transaction_date.month - 1]
        val = valor_despesa_sienge(real.value, plid, real.category, planos_redutora)

        credor = real.creditor_name or "Sem credor"
        doc_name = real.document_name or "—"
        doc_num = real.document_number or "—"
        titulo = real.bill_id or "—"

        t_key = (credor, doc_name, doc_num, titulo)
        if t_key not in node["transacoes"]:
            node["transacoes"][t_key] = {
                "credor": credor,
                "documento_nome": doc_name,
                "documento_numero": doc_num,
                "titulo": titulo,
                "valores": {m: 0.0 for m in MESES_STR + ["total"]},
            }

        node["transacoes"][t_key]["valores"][mes_str] += val
        node["transacoes"][t_key]["valores"]["total"] += val

    resultado = []
    for _key, node in detalhamento_map.items():
        node["transacoes"] = list(node["transacoes"].values())
        resultado.append(node)

    response = {
        "ano": ano,
        "is_consolidado": desp_data.get("is_consolidado", consolidado),
        "matriz": resultado,
        "fonte_realizado_detalhe": FONTE_REALIZADO_DESPESAS,
    }
    if holding_mldu:
        response["holding_mldu"] = True
        response["holding_avisos"] = desp_data.get("holding_avisos") or []
    return response
