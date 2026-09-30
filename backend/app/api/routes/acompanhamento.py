from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, and_
from typing import List, Dict, Any, Optional
from app.api.deps import get_db, get_current_user, get_active_department
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.actual_transaction import ActualTransaction
from app.models.departamento import Departamento
from app.models.financial_plan import FinancialPlan
from app.models.cost_center import CostCenter
from app.models.payment_plan import PaymentPlan
from app.services.calculations import calculo_variacao_rs, calculo_variacao_perc, calculo_saldo_despesas
from app.core.roles import is_gestor_user
from app.services.periodos import MESES_STR
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.services.budget_shared import (
    list_forecast_versoes_disponiveis,
    build_empresas_map,
    build_opcoes_produtos,
)
from app.services.sharepoint_departamento import fix_forecasts_sharepoint_sem_departamento
from app.services.realizado_sienge import (
    FONTE_REALIZADO_DESPESAS,
    FONTE_REALIZADO_RECEITAS,
    agregar_realizado_despesas_sienge,
    agregar_realizado_receitas_sienge,
)

router = APIRouter()

def get_produtos_permitidos(db: Session, dept) -> List[int]:
    from app.services.departamento_leitura import produtos_ids_leitura
    return produtos_ids_leitura(db, dept)

def get_planos_permitidos(db: Session, dept, tp_conta: str = None) -> List[int]:
    from app.services.departamento_leitura import planos_ids_leitura
    return planos_ids_leitura(db, dept, tp_conta)

@router.get("/despesas/{ano}")
def get_acompanhamento_despesas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user),
    forecast_id: Optional[int] = None,
    realizado_agrupado: bool = False,
):
    consolidado = False  # Onda A: legado (todos dept.) desativado
    is_consolidado = False
    if consolidado and is_gestor_user(current_user):
        is_consolidado = True
        produtos_permitidos = [p.id for p in db.query(CostCenter).all()]
        planos_permitidos = [p.id for p in db.query(FinancialPlan).filter(FinancialPlan.tp_conta == 'R', FinancialPlan.db_id.like("2%")).all()]
    else:
        produtos_permitidos = get_produtos_permitidos(db, dept)
        planos_permitidos = get_planos_permitidos(db, dept, 'D')

    orc_query = db.query(Orcamento).filter(Orcamento.ano == ano, Orcamento.tipo == 'DESPESAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        orc_query = orc_query.filter(criterio_departamento(Orcamento.departamento_id, db, dept))
    if is_consolidado:
        o_ref = orc_query.filter(Orcamento.status.in_(["Aprovado", "Fechado"])).order_by(Orcamento.id.desc()).first()
        if not o_ref: o_ref = orc_query.order_by(Orcamento.id.desc()).first()
        orcamentos = orc_query.filter(Orcamento.descricao == o_ref.descricao).all() if o_ref else []
    else:
        from app.services.departamento_leitura import escolher_documentos_leitura
        orcamentos = escolher_documentos_leitura(orc_query, Orcamento, dept)

    fc_query = db.query(Forecast).filter(Forecast.ano == ano, Forecast.tipo == 'DESPESAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        fc_query = fc_query.filter(criterio_departamento(Forecast.departamento_id, db, dept))
    if forecast_id:
        ref_forecast = db.query(Forecast).filter(Forecast.id == forecast_id, Forecast.tipo == 'DESPESAS').first()
        if ref_forecast:
            if is_consolidado:
                forecasts = fc_query.filter(Forecast.descricao == ref_forecast.descricao).all()
            else:
                f_ref = db.query(Forecast).filter(
                    Forecast.ano == ano, 
                    Forecast.tipo == 'DESPESAS', 
                    Forecast.descricao == ref_forecast.descricao,
                    Forecast.departamento_id == ref_forecast.departamento_id
                ).first()
                forecasts = [f_ref] if f_ref else []
        else:
            forecasts = []
    else:
        if is_consolidado:
            f_ref = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f_ref: f_ref = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = fc_query.filter(Forecast.descricao == f_ref.descricao).all() if f_ref else []
        else:
            from app.services.departamento_leitura import escolher_documentos_leitura
            forecasts = escolher_documentos_leitura(fc_query, Forecast, dept)

    active_forecast_id = forecasts[0].id if forecasts else None

    if not is_consolidado:
        from app.services.departamento_leitura import eh_diretoria

        # Diretoria: não expandir planos do doc Corporativo (senão vaza orçado da empresa).
        if not eh_diretoria(dept):
            extra_prod = []
            extra_plan = []
            for orcamento in orcamentos:
                extra_prod.extend([i.produto_id for i in getattr(orcamento, 'itens_despesa', [])])
                extra_plan.extend([i.plano_financeiro_id for i in getattr(orcamento, 'itens_despesa', [])])
            for forecast in forecasts:
                extra_prod.extend([i.produto_id for i in getattr(forecast, 'itens_despesa', [])])
                extra_plan.extend([i.plano_financeiro_id for i in getattr(forecast, 'itens_despesa', [])])
            produtos_permitidos = list(set(produtos_permitidos + extra_prod))
            planos_permitidos = list(set(planos_permitidos + extra_plan))

    if not produtos_permitidos or not planos_permitidos:
        return {"ano": ano, "itens": [], "is_consolidado": is_consolidado, "active_forecast_id": active_forecast_id}

    matriz = {}
    def init_key(prod_id, plano_id):
        if (prod_id, plano_id) not in matriz:
            matriz[(prod_id, plano_id)] = {
                "produto_id": prod_id,
                "plano_financeiro_id": plano_id,
                "orcado": {m: 0.0 for m in MESES_STR},
                "forecast": {m: 0.0 for m in MESES_STR},
                "realizado": {m: 0.0 for m in MESES_STR}
            }

    db_planos = db.query(FinancialPlan).filter(FinancialPlan.id.in_(planos_permitidos)).all()
    planos_id = {p.name: p.id for p in db_planos}
    planos_redutora = {p.id: p.fl_redutora for p in db_planos}
    planos_nomes = {p.id: str(p.name).lower() for p in db_planos}

    for orcamento in orcamentos:
        for item in getattr(orcamento, "itens_despesa", []):
            if item.produto_id in produtos_permitidos and item.plano_financeiro_id in planos_permitidos:
                init_key(item.produto_id, item.plano_financeiro_id)
                plano_nome = planos_nomes.get(item.plano_financeiro_id, "")
                is_redutora = (str(planos_redutora.get(item.plano_financeiro_id)).strip().upper() == "S" or "reten" in plano_nome)
                for mes in MESES_STR:
                    val = getattr(item, mes) or 0.0
                    if is_redutora: val = -abs(val)
                    matriz[(item.produto_id, item.plano_financeiro_id)]["orcado"][mes] += val

    for forecast in forecasts:
        for item in getattr(forecast, "itens_despesa", []):
            if item.produto_id in produtos_permitidos and item.plano_financeiro_id in planos_permitidos:
                init_key(item.produto_id, item.plano_financeiro_id)
                plano_nome = planos_nomes.get(item.plano_financeiro_id, "")
                is_redutora = (str(planos_redutora.get(item.plano_financeiro_id)).strip().upper() == "S" or "reten" in plano_nome)
                for mes in MESES_STR:
                    val = getattr(item, mes) or 0.0
                    if is_redutora: val = -abs(val)
                    matriz[(item.produto_id, item.plano_financeiro_id)]["forecast"][mes] += val

    agregar_realizado_despesas_sienge(
        matriz, init_key, db, ano, produtos_permitidos, planos_permitidos, dept=dept,
        agrupado=realizado_agrupado,
    )

    resultado = []
    for k, v in matriz.items():
        v["orcado"]["total"] = sum(v["orcado"][m] for m in MESES_STR)
        v["forecast"]["total"] = sum(v["forecast"][m] for m in MESES_STR)
        v["realizado"]["total"] = sum(v["realizado"][m] for m in MESES_STR)

        v["saldo_orcado"] = {m: calculo_saldo_despesas(v["orcado"][m], v["realizado"][m]) for m in MESES_STR + ["total"]}
        v["saldo_forecast"] = {m: calculo_saldo_despesas(v["forecast"][m], v["realizado"][m]) for m in MESES_STR + ["total"]}
        
        v["desvio_orcado"] = {m: calculo_variacao_perc(v["realizado"][m], v["orcado"][m]) for m in MESES_STR + ["total"]}
        v["desvio_forecast"] = {m: calculo_variacao_perc(v["realizado"][m], v["forecast"][m]) for m in MESES_STR + ["total"]}

        resultado.append(v)

    versoes = list_forecast_versoes_disponiveis(db, ano, "DESPESAS", dept.id)
    produtos_list = db.query(CostCenter).filter(CostCenter.id.in_(produtos_permitidos)).all()
    empresas_map = build_empresas_map(db)
    # Todos inclui realizado de planos fora do catálogo de despesa (ex.: retenção 1%).
    # O rótulo precisa desses ids; os valores da matriz não mudam.
    ids_rotulo = {pid for pid in planos_permitidos if pid is not None}
    ids_rotulo.update(
        v["plano_financeiro_id"] for v in resultado if v.get("plano_financeiro_id") is not None
    )

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "ano": ano,
        "is_consolidado": is_consolidado,
        "itens": resultado,
        "opcoes_produtos": build_opcoes_produtos(produtos_list, empresas_map),
        "opcoes_planos": [{"id": p.id, "nome": p.name} for p in db.query(FinancialPlan).filter(FinancialPlan.id.in_(ids_rotulo)).all()],
        "versoes_disponiveis": versoes,
        "active_forecast_id": active_forecast_id,
        "realizado_fonte": FONTE_REALIZADO_DESPESAS,
        },
        item_kind="acom_despesas",
    )

@router.get("/receitas/{ano}")
def get_acompanhamento_receitas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user),
    forecast_id: Optional[int] = None,
    realizado_agrupado: bool = False,
):
    consolidado = False  # Onda A: legado (todos dept.) desativado
    is_consolidado = False
    if consolidado and is_gestor_user(current_user):
        is_consolidado = True
        produtos_permitidos = [p.id for p in db.query(CostCenter).all()]
        planos_permitidos = [p.id for p in db.query(FinancialPlan).filter(FinancialPlan.tp_conta == 'R', FinancialPlan.db_id.like("1%")).all()]
    else:
        produtos_permitidos = get_produtos_permitidos(db, dept)
        planos_permitidos = get_planos_permitidos(db, dept, 'R')

    orc_query = db.query(Orcamento).filter(Orcamento.ano == ano, Orcamento.tipo == 'RECEITAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        orc_query = orc_query.filter(criterio_departamento(Orcamento.departamento_id, db, dept))
    if is_consolidado:
        o_ref = orc_query.filter(Orcamento.status.in_(["Aprovado", "Fechado"])).order_by(Orcamento.id.desc()).first()
        if not o_ref: o_ref = orc_query.order_by(Orcamento.id.desc()).first()
        orcamentos = orc_query.filter(Orcamento.descricao == o_ref.descricao).all() if o_ref else []
    else:
        from app.services.departamento_leitura import escolher_documentos_leitura
        orcamentos = escolher_documentos_leitura(orc_query, Orcamento, dept)

    fc_query = db.query(Forecast).filter(Forecast.ano == ano, Forecast.tipo == 'RECEITAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        fc_query = fc_query.filter(criterio_departamento(Forecast.departamento_id, db, dept))
    if forecast_id:
        ref_forecast = db.query(Forecast).filter(Forecast.id == forecast_id, Forecast.tipo == 'RECEITAS').first()
        if ref_forecast:
            if is_consolidado:
                forecasts = fc_query.filter(Forecast.descricao == ref_forecast.descricao).all()
            else:
                f_ref = db.query(Forecast).filter(
                    Forecast.ano == ano, 
                    Forecast.tipo == 'RECEITAS', 
                    Forecast.descricao == ref_forecast.descricao,
                    Forecast.departamento_id == ref_forecast.departamento_id
                ).first()
                forecasts = [f_ref] if f_ref else []
        else:
            forecasts = []
    else:
        if is_consolidado:
            f_ref = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f_ref: f_ref = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = fc_query.filter(Forecast.descricao == f_ref.descricao).all() if f_ref else []
        else:
            from app.services.departamento_leitura import escolher_documentos_leitura
            forecasts = escolher_documentos_leitura(fc_query, Forecast, dept)

    active_forecast_id = forecasts[0].id if forecasts else None

    if not is_consolidado:
        from app.services.departamento_leitura import eh_diretoria

        if not eh_diretoria(dept):
            extra_prod = []
            extra_plan = []
            for orcamento in orcamentos:
                extra_prod.extend([i.produto_id for i in getattr(orcamento, 'itens_despesa', [])])
                extra_plan.extend([i.plano_financeiro_id for i in getattr(orcamento, 'itens_despesa', [])])
            for forecast in forecasts:
                extra_prod.extend([i.produto_id for i in getattr(forecast, 'itens_despesa', [])])
                extra_plan.extend([i.plano_financeiro_id for i in getattr(forecast, 'itens_despesa', [])])
            produtos_permitidos = list(set(produtos_permitidos + extra_prod))
            planos_permitidos = list(set(planos_permitidos + extra_plan))

    if not produtos_permitidos or not planos_permitidos:
        return {"ano": ano, "itens": [], "is_consolidado": is_consolidado, "active_forecast_id": active_forecast_id}

    matriz = {}
    def init_key(prod_id, plano_id):
        if (prod_id, plano_id) not in matriz:
            matriz[(prod_id, plano_id)] = {
                "produto_id": prod_id,
                "plano_financeiro_id": plano_id,
                "orcado": {m: 0.0 for m in MESES_STR},
                "forecast": {m: 0.0 for m in MESES_STR},
                "realizado": {m: 0.0 for m in MESES_STR}
            }

    db_planos = db.query(FinancialPlan).filter(FinancialPlan.id.in_(planos_permitidos)).all()
    planos_id = {p.name: p.id for p in db_planos}
    planos_redutora = {p.id: p.fl_redutora for p in db_planos}
    planos_nomes = {p.id: str(p.name).lower() for p in db_planos}

    for orcamento in orcamentos:
        for item in getattr(orcamento, "itens_despesa", []):
            if item.produto_id in produtos_permitidos and item.plano_financeiro_id in planos_permitidos:
                init_key(item.produto_id, item.plano_financeiro_id)
                plano_nome = planos_nomes.get(item.plano_financeiro_id, "")
                is_redutora = (str(planos_redutora.get(item.plano_financeiro_id)).strip().upper() == "S" or "reten" in plano_nome)
                for mes in MESES_STR:
                    val = getattr(item, mes) or 0.0
                    if is_redutora: val = -abs(val)
                    matriz[(item.produto_id, item.plano_financeiro_id)]["orcado"][mes] += val

    for forecast in forecasts:
        for item in getattr(forecast, "itens_despesa", []):
            if item.produto_id in produtos_permitidos and item.plano_financeiro_id in planos_permitidos:
                init_key(item.produto_id, item.plano_financeiro_id)
                plano_nome = planos_nomes.get(item.plano_financeiro_id, "")
                is_redutora = (str(planos_redutora.get(item.plano_financeiro_id)).strip().upper() == "S" or "reten" in plano_nome)
                for mes in MESES_STR:
                    val = getattr(item, mes) or 0.0
                    if is_redutora: val = -abs(val)
                    matriz[(item.produto_id, item.plano_financeiro_id)]["forecast"][mes] += val

    agregar_realizado_receitas_sienge(
        matriz, init_key, db, ano, produtos_permitidos, planos_permitidos,
        agrupado=realizado_agrupado,
    )

    resultado = []
    for k, v in matriz.items():
        v["orcado"]["total"] = sum(v["orcado"][m] for m in MESES_STR)
        v["forecast"]["total"] = sum(v["forecast"][m] for m in MESES_STR)
        v["realizado"]["total"] = sum(v["realizado"][m] for m in MESES_STR)

        v["saldo_orcado"] = {m: calculo_variacao_rs(v["realizado"][m], v["orcado"][m]) for m in MESES_STR + ["total"]}
        v["saldo_forecast"] = {m: calculo_variacao_rs(v["realizado"][m], v["forecast"][m]) for m in MESES_STR + ["total"]}
        
        v["desvio_orcado"] = {m: calculo_variacao_perc(v["realizado"][m], v["orcado"][m]) for m in MESES_STR + ["total"]}
        v["desvio_forecast"] = {m: calculo_variacao_perc(v["realizado"][m], v["forecast"][m]) for m in MESES_STR + ["total"]}

        resultado.append(v)

    versoes = list_forecast_versoes_disponiveis(db, ano, "RECEITAS", dept.id)
    produtos_list = db.query(CostCenter).filter(CostCenter.id.in_(produtos_permitidos)).all()
    empresas_map = build_empresas_map(db)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "ano": ano,
        "is_consolidado": is_consolidado,
        "itens": resultado,
        "opcoes_produtos": build_opcoes_produtos(produtos_list, empresas_map),
        "opcoes_planos": [{"id": p.id, "nome": p.name} for p in db.query(FinancialPlan).filter(FinancialPlan.id.in_(planos_permitidos)).all()],
        "versoes_disponiveis": versoes,
        "active_forecast_id": active_forecast_id,
        "realizado_fonte": FONTE_REALIZADO_RECEITAS,
        },
        item_kind="acom_receitas",
    )

@router.get("/vendas/{ano}")
def get_acompanhamento_vendas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user),
    forecast_id: Optional[int] = None
):
    fix_forecasts_sharepoint_sem_departamento(db)
    consolidado = False  # Onda A: legado (todos dept.) desativado
    is_consolidado = False
    if consolidado and is_gestor_user(current_user):
        is_consolidado = True
        produtos_permitidos = [p.id for p in db.query(CostCenter).all()]
    else:
        produtos_permitidos = get_produtos_permitidos(db, dept)

    orc_query = db.query(Orcamento).filter(Orcamento.ano == ano, Orcamento.tipo == 'VENDAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        orc_query = orc_query.filter(criterio_departamento(Orcamento.departamento_id, db, dept))
    if is_consolidado:
        o_ref = orc_query.filter(Orcamento.status.in_(["Aprovado", "Fechado"])).order_by(Orcamento.id.desc()).first()
        if not o_ref: o_ref = orc_query.order_by(Orcamento.id.desc()).first()
        orcamentos = orc_query.filter(Orcamento.descricao == o_ref.descricao).all() if o_ref else []
    else:
        from app.services.departamento_leitura import escolher_documentos_leitura
        orcamentos = escolher_documentos_leitura(orc_query, Orcamento, dept)

    fc_query = db.query(Forecast).filter(Forecast.ano == ano, Forecast.tipo == 'VENDAS')
    if not is_consolidado:
        from app.services.departamento_leitura import criterio_departamento
        fc_query = fc_query.filter(criterio_departamento(Forecast.departamento_id, db, dept))
    if forecast_id:
        ref_forecast = db.query(Forecast).filter(Forecast.id == forecast_id, Forecast.tipo == 'VENDAS').first()
        if ref_forecast:
            if is_consolidado:
                forecasts = fc_query.filter(Forecast.descricao == ref_forecast.descricao).all()
            else:
                f_ref = db.query(Forecast).filter(
                    Forecast.ano == ano, 
                    Forecast.tipo == 'VENDAS', 
                    Forecast.descricao == ref_forecast.descricao,
                    Forecast.departamento_id == ref_forecast.departamento_id
                ).first()
                forecasts = [f_ref] if f_ref else []
        else:
            forecasts = []
    else:
        if is_consolidado:
            f_ref = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f_ref: f_ref = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = fc_query.filter(Forecast.descricao == f_ref.descricao).all() if f_ref else []
        else:
            from app.services.departamento_leitura import escolher_documentos_leitura
            forecasts = escolher_documentos_leitura(fc_query, Forecast, dept)

    active_forecast_id = forecasts[0].id if forecasts else None

    if not is_consolidado:
        extra_prod = []
        for orcamento in orcamentos:
            extra_prod.extend([i.produto_id for i in getattr(orcamento, 'itens_venda', [])])
        for forecast in forecasts:
            extra_prod.extend([i.produto_id for i in getattr(forecast, 'itens_venda', [])])
        produtos_permitidos = list(set(produtos_permitidos + extra_prod))

    if not produtos_permitidos:
        return {
            "ano": ano,
            "itens": [],
            "is_consolidado": is_consolidado,
            "active_forecast_id": active_forecast_id,
            "versoes_disponiveis": list_forecast_versoes_disponiveis(db, ano, "VENDAS", dept.id),
        }

    matriz = {}
    def init_key(prod_id):
        if prod_id not in matriz:
            matriz[prod_id] = {
                "produto_id": prod_id,
                "vendas": {
                    "orcado": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR},
                    "forecast": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR},
                    "realizado": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR}
                },
                "distratos": {
                    "orcado": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR},
                    "forecast": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR},
                    "realizado": {m: {"unidades": 0, "ticket": 0.0, "vgv": 0.0} for m in MESES_STR}
                }
            }

    for orcamento in orcamentos:
        for item in getattr(orcamento, "itens_venda", []):
            if item.produto_id in produtos_permitidos:
                init_key(item.produto_id)
                mes_str = MESES_STR[item.mes - 1]
                target = "distratos" if getattr(item, "is_distrato", False) else "vendas"
                matriz[item.produto_id][target]["orcado"][mes_str]["unidades"] += item.numero_vendas
                matriz[item.produto_id][target]["orcado"][mes_str]["vgv"] += item.vgv

    for forecast in forecasts:
        for item in getattr(forecast, "itens_venda", []):
            if item.produto_id in produtos_permitidos:
                init_key(item.produto_id)
                mes_str = MESES_STR[item.mes - 1]
                target = "distratos" if getattr(item, "is_distrato", False) else "vendas"
                matriz[item.produto_id][target]["forecast"][mes_str]["unidades"] += item.numero_vendas
                matriz[item.produto_id][target]["forecast"][mes_str]["vgv"] += item.vgv

    reais = db.query(ActualTransaction).filter(
        ActualTransaction.transaction_type == "SALE",
        extract('year', ActualTransaction.transaction_date) == ano,
        ActualTransaction.cost_center_id.in_(produtos_permitidos),
        ActualTransaction.is_forecast == False
    ).all()
    
    for real in reais:
        init_key(real.cost_center_id)
        mes_idx = real.transaction_date.month - 1
        mes_str = MESES_STR[mes_idx]
        
        target = "distratos" if real.category == "Distrato" else "vendas"
        
        matriz[real.cost_center_id][target]["realizado"][mes_str]["unidades"] += 1
        
        if target == "vendas":
            matriz[real.cost_center_id]["vendas"]["realizado"][mes_str]["vgv"] += real.value or 0.0
        else:
            if "raw_vgv" not in matriz[real.cost_center_id]["distratos"]["realizado"][mes_str]:
                matriz[real.cost_center_id]["distratos"]["realizado"][mes_str]["raw_vgv"] = 0
            matriz[real.cost_center_id]["distratos"]["realizado"][mes_str]["raw_vgv"] += abs(real.value or 0.0)

    resultado = []
    for k, v in matriz.items():
        # Calcular os totais PRIMEIRO para poder usar os tickets médios anuais como fallback
        for subcat in ["vendas", "distratos"]:
            for tipo in ["orcado", "forecast", "realizado"]:
                v[subcat][tipo]["total"] = {
                    "unidades": sum(v[subcat][tipo][m]["unidades"] for m in MESES_STR),
                    "vgv": sum(v[subcat][tipo][m]["vgv"] for m in MESES_STR),
                }
                v[subcat][tipo]["total"]["ticket"] = v[subcat][tipo]["total"]["vgv"] / v[subcat][tipo]["total"]["unidades"] if v[subcat][tipo]["total"]["unidades"] > 0 else 0

        for subcat in ["vendas", "distratos"]:
            for m in MESES_STR:
                v[subcat]["orcado"][m]["ticket"] = v[subcat]["orcado"][m]["vgv"] / v[subcat]["orcado"][m]["unidades"] if v[subcat]["orcado"][m]["unidades"] > 0 else 0
                v[subcat]["forecast"][m]["ticket"] = v[subcat]["forecast"][m]["vgv"] / v[subcat]["forecast"][m]["unidades"] if v[subcat]["forecast"][m]["unidades"] > 0 else 0
                
                if subcat == "distratos":
                    ticket_medio = v["distratos"]["orcado"][m]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["distratos"]["forecast"][m]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["distratos"]["orcado"]["total"]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["distratos"]["forecast"]["total"]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["vendas"]["orcado"][m]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["vendas"]["orcado"]["total"]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["vendas"]["forecast"]["total"]["ticket"]
                    if ticket_medio == 0: ticket_medio = v["vendas"]["realizado"]["total"]["ticket"]
                    
                    if ticket_medio > 0:
                        v["distratos"]["realizado"][m]["vgv"] = v["distratos"]["realizado"][m]["unidades"] * ticket_medio
                    else:
                        v["distratos"]["realizado"][m]["vgv"] = v["distratos"]["realizado"][m].get("raw_vgv", 0)

                v[subcat]["realizado"][m]["ticket"] = v[subcat]["realizado"][m]["vgv"] / v[subcat]["realizado"][m]["unidades"] if v[subcat]["realizado"][m]["unidades"] > 0 else 0

        v["distratos"]["realizado"]["total"]["vgv"] = sum(v["distratos"]["realizado"][m]["vgv"] for m in MESES_STR)
        v["distratos"]["realizado"]["total"]["ticket"] = v["distratos"]["realizado"]["total"]["vgv"] / v["distratos"]["realizado"]["total"]["unidades"] if v["distratos"]["realizado"]["total"]["unidades"] > 0 else 0

        for subcat in ["vendas", "distratos"]:
            v[f"desvio_orcado_{subcat}"] = {m: calculo_variacao_perc(v[subcat]["realizado"][m]["vgv"], v[subcat]["orcado"][m]["vgv"]) for m in MESES_STR}
            v[f"desvio_orcado_{subcat}"]["total"] = calculo_variacao_perc(v[subcat]["realizado"]["total"]["vgv"], v[subcat]["orcado"]["total"]["vgv"])
            
            v[f"desvio_forecast_{subcat}"] = {m: calculo_variacao_perc(v[subcat]["realizado"][m]["vgv"], v[subcat]["forecast"][m]["vgv"]) for m in MESES_STR}
            v[f"desvio_forecast_{subcat}"]["total"] = calculo_variacao_perc(v[subcat]["realizado"]["total"]["vgv"], v[subcat]["forecast"]["total"]["vgv"])
            
            v[f"desvio_orcado_{subcat}_unid"] = {m: calculo_variacao_perc(v[subcat]["realizado"][m]["unidades"], v[subcat]["orcado"][m]["unidades"]) for m in MESES_STR}
            v[f"desvio_orcado_{subcat}_unid"]["total"] = calculo_variacao_perc(v[subcat]["realizado"]["total"]["unidades"], v[subcat]["orcado"]["total"]["unidades"])
            
            v[f"desvio_forecast_{subcat}_unid"] = {m: calculo_variacao_perc(v[subcat]["realizado"][m]["unidades"], v[subcat]["forecast"][m]["unidades"]) for m in MESES_STR}
            v[f"desvio_forecast_{subcat}_unid"]["total"] = calculo_variacao_perc(v[subcat]["realizado"]["total"]["unidades"], v[subcat]["forecast"]["total"]["unidades"])
            
        resultado.append(v)

    versoes = list_forecast_versoes_disponiveis(db, ano, "VENDAS", dept.id)

    active_forecast_id = forecasts[0].id if forecasts else None

    filtros = get_filtros_ativos(ano, db, current_user)
    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "ano": ano,
        "is_consolidado": is_consolidado,
        "itens": resultado,
        "opcoes_produtos": filtros["centros_custo"],
        "opcoes_planos": filtros["planos_venda"],
        "versoes_disponiveis": versoes,
        "active_forecast_id": active_forecast_id
        },
        item_kind="acom_vendas",
    )

@router.get("/consolidado/{ano}")
def get_acompanhamento_consolidado(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user),
    forecast_id: Optional[int] = None
):
    despesas_res = get_acompanhamento_despesas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id)
    receitas_res = get_acompanhamento_receitas(ano, consolidado, holding_mldu, db, dept, current_user, forecast_id)

    resultado = {
        "orcado": {m: 0.0 for m in MESES_STR + ["total"]},
        "forecast": {m: 0.0 for m in MESES_STR + ["total"]},
        "realizado": {m: 0.0 for m in MESES_STR + ["total"]}
    }

    for res in receitas_res.get("itens", []):
        for m in MESES_STR + ["total"]:
            resultado["orcado"][m] += res["orcado"][m]
            resultado["forecast"][m] += res["forecast"][m]
            resultado["realizado"][m] += res["realizado"][m]

    for desp in despesas_res.get("itens", []):
        for m in MESES_STR + ["total"]:
            resultado["orcado"][m] -= desp["orcado"][m]
            resultado["forecast"][m] -= desp["forecast"][m]
            resultado["realizado"][m] -= desp["realizado"][m]

    desvio_orcado = {m: calculo_variacao_perc(resultado["realizado"][m], resultado["orcado"][m]) for m in MESES_STR + ["total"]}
    desvio_forecast = {m: calculo_variacao_perc(resultado["realizado"][m], resultado["forecast"][m]) for m in MESES_STR + ["total"]}


    versoes_d = despesas_res.get("versoes_disponiveis", [])
    versoes_r = receitas_res.get("versoes_disponiveis", [])

    v_dict = {}
    for v in versoes_d + versoes_r:
        if v["descricao"] not in v_dict or v_dict[v["descricao"]].get("status") == "Importado Sienge":
            v_dict[v["descricao"]] = v
    versoes_consolidadas = list(v_dict.values())

    response = {
        "ano": ano,
        "is_consolidado": despesas_res.get("is_consolidado", False),
        "receitas": receitas_res.get("itens", []),
        "despesas": despesas_res.get("itens", []),
        "opcoes_produtos": receitas_res.get("opcoes_produtos", []) or despesas_res.get("opcoes_produtos", []),
        "opcoes_planos": receitas_res.get("opcoes_planos", []) + despesas_res.get("opcoes_planos", []),
        "versoes_disponiveis": versoes_consolidadas,
        "active_forecast_id": despesas_res.get("active_forecast_id") or receitas_res.get("active_forecast_id"),
        "resultado": {
            "orcado": resultado["orcado"],
            "forecast": resultado["forecast"],
            "realizado": resultado["realizado"],
            "desvio_orcado": desvio_orcado,
            "desvio_forecast": desvio_forecast
        }
    }
    if holding_mldu:
        avisos = list(
            dict.fromkeys(
                (despesas_res.get("holding_avisos") or []) + (receitas_res.get("holding_avisos") or [])
            )
        )
        response["holding_mldu"] = True
        response["holding_avisos"] = avisos
    return response

@router.get("/filtros-ativos/{ano}")
def get_filtros_ativos(
    ano: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    produtos_ids = set()
    planos_ids = set()
    planos_venda_ids = set()

    # 1. Actual Transactions
    transacoes = db.query(ActualTransaction.cost_center_id).filter(func.extract('year', ActualTransaction.transaction_date) == ano).all()
    for t in transacoes:
        if t[0]: produtos_ids.add(t[0])

    # 2. Orcamentos Despesas/Receitas
    orc_itens = db.query(OrcamentoItem.produto_id, OrcamentoItem.plano_financeiro_id).join(Orcamento).filter(Orcamento.ano == ano).all()
    for item in orc_itens:
        if item[0]: produtos_ids.add(item[0])
        if item[1]: planos_ids.add(item[1])

    # 3. Orcamentos Vendas
    orc_vendas = db.query(OrcamentoVendaItem.produto_id, OrcamentoVendaItem.plano_venda_id).join(Orcamento).filter(Orcamento.ano == ano).all()
    for item in orc_vendas:
        if item[0]: produtos_ids.add(item[0])
        if item[1]: planos_venda_ids.add(item[1])

    # 4. Forecast Despesas/Receitas
    for_itens = db.query(ForecastItem.produto_id, ForecastItem.plano_financeiro_id).join(Forecast).filter(Forecast.ano == ano).all()
    for item in for_itens:
        if item[0]: produtos_ids.add(item[0])
        if item[1]: planos_ids.add(item[1])

    # 5. Forecast Vendas
    for_vendas = db.query(ForecastVendaItem.produto_id, ForecastVendaItem.plano_venda_id).join(Forecast).filter(Forecast.ano == ano).all()
    for item in for_vendas:
        if item[0]: produtos_ids.add(item[0])
        if item[1]: planos_venda_ids.add(item[1])

    # Busca Entidades
    produtos = db.query(CostCenter).filter(CostCenter.id.in_(list(produtos_ids))).all() if produtos_ids else []
    planos = db.query(FinancialPlan).filter(FinancialPlan.id.in_(list(planos_ids))).all() if planos_ids else []
    planos_venda = db.query(PaymentPlan).filter(PaymentPlan.id.in_(list(planos_venda_ids))).all() if planos_venda_ids else []

    empresas_map = build_empresas_map(db)
    centros_custo_out = build_opcoes_produtos(produtos, empresas_map)

    empresas_set = set()
    for cc in centros_custo_out:
        if cc["id_empresa"] and cc["nome_empresa"]:
            empresas_set.add((cc["id_empresa"], cc["nome_empresa"]))
    empresas_out = [{"id": e[0], "nome": e[1]} for e in sorted(empresas_set, key=lambda x: x[1])]

    return {
        "centros_custo": centros_custo_out,
        "planos_financeiros": [{"id": p.id, "nome": p.name, "db_id": p.db_id} for p in planos],
        "planos_venda": [{"id": p.id, "nome": getattr(p, "nome", getattr(p, "name", ""))} for p in planos_venda],
        "empresas": empresas_out
    }
