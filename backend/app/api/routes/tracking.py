from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session, joinedload

from typing import Any, List, Dict

from app.db.database import get_db

from app.api import deps

from app.schemas.user import UserResponse

from app.models.viability import Viability

from app.models.phase import Phase

from app.models.cost_center import CostCenter

from app.models.actual_transaction import ActualTransaction

from app.models.unit import Unit

from sqlalchemy import func, or_, cast, String

from app.services.math_engine import calculate_viability_results

from app.models.vision import Vision, FinancialPlanVisionLink

from app.models.financial_plan import FinancialPlan

from collections import defaultdict

import numpy_financial as npf

import pandas as pd

from datetime import datetime



router = APIRouter()


def _ano_mes_transacao():
    """Mês YYYY-MM. No Postgres a coluna é DATE e substr direto nela não existe."""
    return func.substr(cast(ActualTransaction.transaction_date, String), 1, 7)


def _projetar_vgv_estoque_no_fluxo(anual_cf_fcst, monthly_net_cf_fcst, estoque_atual, avg_vendas_por_mes, avg_vgv_per_unit, weights_by_installments, proj_month, proj_year, max_months=600):
    """Lança o VGV de estoque nos mesmos meses da projeção mês a mês."""
    if not (estoque_atual > 0 and avg_vendas_por_mes > 0):
        return
    series = []
    estoque_restante = float(estoque_atual)
    while estoque_restante > 1e-9 and len(series) < max_months:
        vendas_do_mes = min(avg_vendas_por_mes, estoque_restante)
        estoque_restante -= vendas_do_mes
        series.append(vendas_do_mes * avg_vgv_per_unit)
    if not series:
        return
    insts = []
    for inst, weight in weights_by_installments.items():
        inst_i = int(inst)
        if inst_i > 0 and weight:
            insts.append((inst_i, float(weight)))
    if not insts:
        return
    max_inst = max(inst_i for inst_i, _ in insts)
    diff = [0.0] * (len(series) + max_inst + 1)
    for inst_i, weight in insts:
        for s, vgv_do_mes in enumerate(series):
            parcela = (vgv_do_mes * weight) / inst_i
            if parcela > 0:
                diff[s] += parcela
                diff[s + inst_i] -= parcela
    running = 0.0
    for idx, delta in enumerate(diff):
        running += delta
        if abs(running) < 1e-6:
            running = 0.0
            continue
        y = proj_year + (proj_month - 1 + idx) // 12
        m = (proj_month - 1 + idx) % 12 + 1
        anual_cf_fcst[str(y)]["Entradas"] += running
        monthly_net_cf_fcst[f"{y}-{m:02d}"] += running


def _prefetch_tracking_actuals(db, cc_ids):
    """Uma leitura para todos os centros da lista. As contas continuam em _calc_actuals_for_cc."""
    cc_ids = list({cid for cid in cc_ids if cid is not None})
    sales_by = defaultdict(list)
    real_by = defaultdict(list)
    fcst_by = defaultdict(list)
    units_by = defaultdict(list)
    cc_by = {}
    if not cc_ids:
        return {"sales": sales_by, "real": real_by, "fcst": fcst_by, "units": units_by, "ccs": cc_by}

    sales = db.query(ActualTransaction).options(joinedload(ActualTransaction.unit)).filter(
        ActualTransaction.cost_center_id.in_(cc_ids),
        ActualTransaction.is_forecast == False,
        ActualTransaction.transaction_type == "SALE",
    ).all()
    for sale in sales:
        sales_by[sale.cost_center_id].append(sale)

    real_rows = db.query(
        ActualTransaction.cost_center_id,
        _ano_mes_transacao().label("mes"),
        ActualTransaction.category,
        ActualTransaction.transaction_type,
        func.sum(ActualTransaction.value).label("total_value"),
        func.count(ActualTransaction.id).label("count"),
    ).filter(
        ActualTransaction.cost_center_id.in_(cc_ids),
        ActualTransaction.is_forecast == False,
        ActualTransaction.transaction_type != "SALE",
    ).group_by(
        ActualTransaction.cost_center_id,
        _ano_mes_transacao(),
        ActualTransaction.category,
        ActualTransaction.transaction_type,
    ).all()
    for row in real_rows:
        real_by[row.cost_center_id].append(row)

    fcst_rows = db.query(
        ActualTransaction.cost_center_id,
        _ano_mes_transacao().label("mes"),
        ActualTransaction.category,
        ActualTransaction.transaction_type,
        func.sum(ActualTransaction.value).label("total_value"),
        func.count(ActualTransaction.id).label("count"),
    ).filter(
        ActualTransaction.cost_center_id.in_(cc_ids),
        ActualTransaction.is_forecast == True,
    ).group_by(
        ActualTransaction.cost_center_id,
        _ano_mes_transacao(),
        ActualTransaction.category,
        ActualTransaction.transaction_type,
    ).all()
    for row in fcst_rows:
        fcst_by[row.cost_center_id].append(row)

    estoque_status = ["D", "R", "C", "P", "G"]
    for unit in db.query(Unit).filter(Unit.cost_center_id.in_(cc_ids), Unit.status.in_(estoque_status)).all():
        units_by[unit.cost_center_id].append(unit)
    for cc in db.query(CostCenter).filter(CostCenter.id.in_(cc_ids)).all():
        cc_by[cc.id] = cc
    return {"sales": sales_by, "real": real_by, "fcst": fcst_by, "units": units_by, "ccs": cc_by}


def _calc_actuals_for_cc(db: Session, cc_id: int, active_rules: dict = None, mult_apportioned: float = 1.0, mult_default: float = 1.0, cached_cat_to_group: dict = None, prefetched=None, kpis_only: bool = False):

    """Calcula os valores realizados de um CC para DRE e Fluxo de Caixa.

    Combina transações realizadas (is_forecast=False) com previsões (is_forecast=True).

    Aplica rateio de parceria em nível de transação se active_rules for fornecido.

    """

    # 1. Buscar transações de VENDAS separadamente (para ter a entidade unit e área)

    if prefetched is not None:
        transactions_sales = prefetched["sales"].get(cc_id, [])
    else:
        transactions_sales = db.query(ActualTransaction).options(joinedload(ActualTransaction.unit)).filter_by(

            cost_center_id=cc_id,

            is_forecast=False,

            transaction_type='SALE'

        ).all()

    

    # 2. Agregação no banco de dados para INCOME e OUTCOME realizados

    from sqlalchemy import func

    if prefetched is not None:
        real_agg = prefetched["real"].get(cc_id, [])
    else:
        real_agg = db.query(

        _ano_mes_transacao().label("mes"),

        ActualTransaction.category,

        ActualTransaction.transaction_type,

        func.sum(ActualTransaction.value).label("total_value"),

        func.count(ActualTransaction.id).label("count")

    ).filter(

        ActualTransaction.cost_center_id == cc_id,

        ActualTransaction.is_forecast == False,

        ActualTransaction.transaction_type != 'SALE'

    ).group_by(

        _ano_mes_transacao(),

        ActualTransaction.category,

        ActualTransaction.transaction_type

    ).all()



    # 3. Agregação no banco de dados para INCOME e OUTCOME previstos (is_forecast=True)

    if prefetched is not None:
        fcst_agg = prefetched["fcst"].get(cc_id, [])
    else:
        fcst_agg = db.query(

        _ano_mes_transacao().label("mes"),

        ActualTransaction.category,

        ActualTransaction.transaction_type,

        func.sum(ActualTransaction.value).label("total_value"),

        func.count(ActualTransaction.id).label("count")

    ).filter(

        ActualTransaction.cost_center_id == cc_id,

        ActualTransaction.is_forecast == True

    ).group_by(

        _ano_mes_transacao(),

        ActualTransaction.category,

        ActualTransaction.transaction_type

    ).all()



    anual_cf_real = defaultdict(lambda: {"Entradas": 0, "Tributos": 0, "Terreno": 0, "Obras": 0, "Projetos": 0, "Marketing": 0, "Comercial": 0, "Administrativas": 0, "Saidas": 0, "Devolucao_Distratos": 0})

    anual_cf_fcst = defaultdict(lambda: {"Entradas": 0, "Tributos": 0, "Terreno": 0, "Obras": 0, "Projetos": 0, "Marketing": 0, "Comercial": 0, "Administrativas": 0, "Saidas": 0, "Devolucao_Distratos": 0})

    # (mantemos anual_cf como alias dos realizados para os KPIs de TIR/Payback)

    anual_cf = anual_cf_real

    

    vgv_vendido = 0.0

    distratos = 0.0

    impostos = 0.0

    recebimentos = 0.0

    terreno = 0.0

    projetos = 0.0

    obras = 0.0

    adm_obra = 0.0

    custo_extra_obra = 0.0

    marketing = 0.0

    comercial = 0.0

    administrativas = 0.0

    despesas_extras = 0.0

    funding = 0.0

    

    sales_by_month = defaultdict(list)

    distratos_by_month = defaultdict(list)

    monthly_net_cf_real = defaultdict(float)  # Fluxo mensal realizado (para TIR/Payback)

    monthly_net_cf_fcst = defaultdict(float)  # Fluxo mensal previsto

    monthly_revenues_real = defaultdict(float) # Apenas receitas realizadas

    monthly_revenues_fcst = defaultdict(float) # Receitas previstas



    cat_to_group = cached_cat_to_group

    if cat_to_group is None:

        cat_to_group = {}

        vision = db.query(Vision).filter_by(is_padrao=True).first()

        if not vision:

            vision = db.query(Vision).first()

        if vision:
            node_map = {n.id: n.descricao.strip().upper() for n in vision.nodes if n.descricao}
            if node_map:
                links = db.query(FinancialPlanVisionLink, FinancialPlan).join(
                    FinancialPlan, FinancialPlan.id == FinancialPlanVisionLink.financial_plan_id
                ).filter(
                    FinancialPlanVisionLink.vision_node_id.in_(node_map.keys())
                ).all()
                for link, fp in links:
                    if fp:
                        cat_to_group[fp.name.strip().lower()] = node_map[link.vision_node_id]



    has_revenue_rule = False

    if active_rules is not None:

        has_revenue_rule = any(active_rules.get(k, False) for k in active_rules if "receita" in k.lower() or "venda" in k.lower() or "entrada" in k.lower() or "recebimento" in k.lower())



    def _process_sale(t):

        nonlocal vgv_vendido, distratos

        if t.transaction_date:

            mes = t.transaction_date[:7] if isinstance(t.transaction_date, str) else t.transaction_date.strftime("%Y-%m")

        else:

            mes = "N/A"

        val = t.value

        

        if active_rules is not None:

            if has_revenue_rule:

                val = val * mult_apportioned

            else:

                val = val * mult_default



        if t.category == "VGV Vendido":

            vgv_vendido += val

            sales_by_month[mes].append(t)

        elif t.category == "Distrato":

            distratos += abs(val)

            if mes != "N/A":

                distratos_by_month[mes].append(t)



    def _process_aggregated(transaction_type, category, total_value, raw_mes, target_anual_cf, target_monthly_cf, is_real, target_monthly_revenues=None):

        """Processa uma linha agregada, acumulando nos dicionários corretos."""

        nonlocal distratos, recebimentos, impostos, terreno, projetos, obras, adm_obra, custo_extra_obra, marketing, comercial, administrativas, despesas_extras, funding



        mes = raw_mes if raw_mes else "N/A"

        ano = mes[:4] if mes != "N/A" else "N/A"

        cat = category.lower().strip() if category else ""

        val = abs(total_value) if total_value else 0.0



        if active_rules is not None:

            is_checked = False

            group = cat_to_group.get(cat, "")

            # Map the DRE node to the UI rule keys

            if "receita" in group.lower() or transaction_type == "INCOME" or "venda" in cat:

                is_checked = active_rules.get("receitas", False)

            elif "imposto" in group.lower() or "reten" in group.lower() or "tributo" in cat:

                is_checked = active_rules.get("impostos", False)

            elif "terreno" in group.lower() or "terreno" in cat:

                is_checked = active_rules.get("terreno", False)

            elif "obra" in group.lower() or "custo" in group.lower():

                is_checked = active_rules.get("obras", False)

            elif "projeto" in group.lower():

                is_checked = active_rules.get("projetos", False)

            elif "marketing" in group.lower():

                is_checked = active_rules.get("marketing", False)

            elif "comercial" in group.lower() or "corretagem" in cat or "comiss" in cat:

                is_checked = active_rules.get("comerciais", False)

            elif "distrato" in group.lower() or "cancelamento" in group.lower() or "distrat" in cat:

                is_checked = active_rules.get("distratos", False)

            else:

                is_checked = active_rules.get("administrativas", False)



            if is_checked:



                val = val * mult_apportioned

            else:

                val = val * mult_default



        if transaction_type == "INCOME":

            if is_real:

                recebimentos += val

            if ano != "N/A":

                target_anual_cf[ano]["Entradas"] += val

            if mes != "N/A":

                target_monthly_cf[mes] += val

                if target_monthly_revenues is not None:

                    target_monthly_revenues[mes] += val



        elif transaction_type == "OUTCOME":

            group = cat_to_group.get(cat, "")



            if "DISTRATO" in group or "CANCELAMENTO" in group or "distrat" in cat:

                # O VGV distratado e a contagem de distratos de vendas (unidades)

                # JÁ SÃO computados no _process_sale (transaction_type == "SALE").

                # Aqui no OUTCOME (Contas a Pagar), só contabilizamos o dinheiro efetivamente devolvido ao cliente.

                if ano != "N/A":

                    target_anual_cf[ano]["Devolucao_Distratos"] += val

                if mes != "N/A":

                    target_monthly_cf[mes] -= val

                # Não entra no fluxo de caixa como saída padrão para não inflar as despesas operacionais

                return



            if ano != "N/A":

                target_anual_cf[ano]["Saidas"] += val

            if mes != "N/A":

                target_monthly_cf[mes] -= val



            if group in ["IMPOSTOS SOBRE VENDAS", "RETENÇÕES", "IMPOSTOS"]:

                impostos += val

                if ano != "N/A": target_anual_cf[ano]["Tributos"] += val

            elif group in ["AQUISIÇÃO DE NOVAS ÁREAS", "REPASSES TERRENISTAS"]:

                terreno += val

                if ano != "N/A": target_anual_cf[ano]["Terreno"] += val

            elif group in ["PROJETOS E APROVAÇOES", "PROJETOS E APROVAÇÕES"]:

                projetos += val

                if ano != "N/A": target_anual_cf[ano]["Projetos"] += val

            elif group in ["MARKETING"]:

                marketing += val

                if ano != "N/A": target_anual_cf[ano]["Marketing"] += val

            elif group in ["DESPESAS COMERCIAIS"]:

                comercial += val

                if ano != "N/A": target_anual_cf[ano]["Comercial"] += val

            elif group in ["OBRAS", "DESPESAS COM MANUTENÇÃO DE EMPREENDIMENTO"]:

                obras += val

                if ano != "N/A": target_anual_cf[ano]["Obras"] += val

            elif group in ["ADMINISTRAÇÃO DA OBRA"]:

                adm_obra += val

                if ano != "N/A": target_anual_cf[ano]["Obras"] += val

            elif group in ["CUSTOS EXTRAS DE OBRAS"]:

                custo_extra_obra += val

                if ano != "N/A": target_anual_cf[ano]["Obras"] += val

            elif group in ["ADMINISTRATIVAS", "PESSOAL", "DESPESAS COM ESTOQUE", "ADIANTAMENTO A FORNECEDORES"]:

                administrativas += val

                if ano != "N/A": target_anual_cf[ano]["Administrativas"] += val

            elif group in ["DESPESAS NAO OPERACIONAIS", "DESPESAS EXTRAS"]:

                despesas_extras += val

                if ano != "N/A": target_anual_cf[ano]["Administrativas"] += val

            elif group in ["FUNDING", "JUROS", "EMPRESTIMOS", "ESTRUTURAÇÃO"]:

                funding += val

                if ano != "N/A": target_anual_cf[ano]["Administrativas"] += val

            else:

                # Fallbacks para caso falte o mapeamento na Visão DFC

                if "IMPOSTOS" in group or "RETEN" in group or any(k in cat for k in ["imposto", "tributo", "irpj", "csll", "pis", "cofins", "iss", "inss", "fgts", "recolhimento"]):

                    if is_real: impostos += val

                    if ano != "N/A": target_anual_cf[ano]["Tributos"] += val

                elif "TERRENO" in group or "terreno" in cat:

                    if is_real: terreno += val

                    if ano != "N/A": target_anual_cf[ano]["Terreno"] += val

                elif "PROJETOS" in group or "projeto" in cat or "aprova" in cat:

                    if is_real: projetos += val

                    if ano != "N/A": target_anual_cf[ano]["Projetos"] += val

                elif "MARKETING" in group or any(k in cat for k in ["agência", "mídia", "ooh", "panflet", "decora", "evento", "maquete"]):

                    if is_real: marketing += val

                    if ano != "N/A": target_anual_cf[ano]["Marketing"] += val

                elif "COMERCIAIS" in group or "VENDAS" in group or any(k in cat for k in ["comercial", "venda", "comiss", "stand", "corretagem"]):

                    if is_real: comercial += val

                    if ano != "N/A": target_anual_cf[ano]["Comercial"] += val

                elif "ADMINISTRATIVA" in group or "PESSOAL" in group or any(k in cat for k in ["cobrança", "jurídica", "viagem", "refeição", "cartório"]):

                    if is_real: administrativas += val

                    if ano != "N/A": target_anual_cf[ano]["Administrativas"] += val

                elif "OBRA" in group or "CUSTO" in group or "REPASSES" in group or any(k in cat for k in ["construç", " obra", "obras", "(obra)", "material", "equipamento", "manutenç", "assistência"]):

                    if is_real: obras += val

                    if ano != "N/A": target_anual_cf[ano]["Obras"] += val

                else:

                    if is_real: administrativas += val

                    if ano != "N/A": target_anual_cf[ano]["Administrativas"] += val



    # Processar transações de VENDAS (uma a uma)

    for t in transactions_sales:

        _process_sale(t)



    # Processar linhas agregadas REALIZADAS

    for row in real_agg:

        _process_aggregated(row.transaction_type, row.category, row.total_value, row.mes, anual_cf_real, monthly_net_cf_real, True, monthly_revenues_real)



    # Processar linhas agregadas PREVISTAS

    for row in fcst_agg:

        _process_aggregated(row.transaction_type, row.category, row.total_value, row.mes, anual_cf_fcst, monthly_net_cf_fcst, False, monthly_revenues_fcst)



    # Calcular preço médio dos ultimos 6 meses com vendas

    sorted_months = sorted(sales_by_month.keys(), reverse=True)

    last_6_months = sorted_months[:6]

    

    total_sales_value = 0.0

    total_sales_area = 0.0

    

    for m in last_6_months:

        for s in sales_by_month[m]:

            if s.unit and s.unit.private_area > 0:

                total_sales_value += s.value

                total_sales_area += s.unit.private_area

                

    avg_price = (total_sales_value / total_sales_area) if total_sales_area > 0 else 0.0

    

    # Calcular VGV de Estoque

    estoque_status = ["D", "R", "C", "P", "G"]

    if prefetched is not None:
        available_units = prefetched["units"].get(cc_id, [])
    else:
        available_units = db.query(Unit).filter(Unit.cost_center_id == cc_id, Unit.status.in_(estoque_status)).all()

    available_area = sum(u.private_area for u in available_units)

    vgv_estoque = available_area * avg_price



    # ---------------------------------------------------------

    # Se houver custo de terreno manual, insere como investimento inicial no primeiro mês do fluxo

    cc = prefetched["ccs"].get(cc_id) if prefetched is not None else db.query(CostCenter).filter(CostCenter.id == cc_id).first()

    if cc and cc.manual_land_cost and float(cc.manual_land_cost) > 0:

        mlc = float(cc.manual_land_cost) * mult_apportioned

        sorted_m = sorted([m for m in monthly_net_cf_real.keys() if m != "N/A"])

        first_m = sorted_m[0] if sorted_m else (datetime.now().strftime("%Y-%m"))

        monthly_net_cf_real[first_m] -= mlc

        if first_m[:4] != "N/A":

            if first_m[:4] not in anual_cf:

                anual_cf[first_m[:4]] = {"Entradas": 0, "Saidas": 0, "Saldo": 0, "Tributos": 0, "Terreno": 0, "Projetos": 0, "Marketing": 0, "Comercial": 0, "Obras": 0, "Administrativas": 0, "Devolucao_Distratos": 0}

            anual_cf[first_m[:4]]["Saidas"] += mlc

            anual_cf[first_m[:4]]["Terreno"] += mlc

            anual_cf[first_m[:4]]["Saldo"] = anual_cf[first_m[:4]].get("Saldo", 0) - mlc

        terreno += mlc



    # ---------------------------------------------------------

    # PROJEÇÃO DE VENDAS FUTURAS EM MEMÓRIA (ÚLTIMOS 6 MESES COM VENDAS)

    # ---------------------------------------------------------

    estoque_atual = len(available_units)

    print(f"[DEBUG] Estoque atual: {estoque_atual}, VGV Estoque: {vgv_estoque}, CC: {cc_id}")

    if estoque_atual > 0:

        # Filtrar meses que tiveram vendas reais (vendas > 0)

        valid_sales_months = sorted([m for m, sales in sales_by_month.items() if m != "N/A" and len(sales) > 0], reverse=True)

        last_6_active_months = valid_sales_months[:6]

        

        print(f"[DEBUG] Últimos 6 meses com vendas: {last_6_active_months}")

        if last_6_active_months:

            total_sales_in_6_months = 0

            total_vgv_in_6_months = 0.0

            weights_by_installments = defaultdict(float)

            

            for m in last_6_active_months:

                total_sales_in_6_months += len(sales_by_month[m])

                for t in sales_by_month[m]:

                    vgv = abs(t.value)

                    total_vgv_in_6_months += vgv

                    inst = t.installments_number or 1

                    if inst <= 0: inst = 1

                    weights_by_installments[inst] += vgv

                    

            avg_vendas_por_mes = total_sales_in_6_months / len(last_6_active_months)

            

            if total_vgv_in_6_months > 0:

                for inst in list(weights_by_installments.keys()):

                    weights_by_installments[inst] /= total_vgv_in_6_months

            else:

                weights_by_installments[1] = 1.0

                

            if avg_vendas_por_mes > 0:

                import datetime as dt

                current_dt = dt.datetime.now()

                proj_month = current_dt.month + 1

                proj_year = current_dt.year

                if proj_month > 12:

                    proj_month = 1

                    proj_year += 1

                avg_vgv_per_unit = vgv_estoque / estoque_atual if estoque_atual > 0 else 0

                _projetar_vgv_estoque_no_fluxo(

                    anual_cf_fcst,

                    monthly_net_cf_fcst,

                    estoque_atual,

                    avg_vendas_por_mes,

                    avg_vgv_per_unit,

                    weights_by_installments,

                    proj_month,

                    proj_year,

                )



    # ---------------------------------------------------------

    # PROJEÇÃO DE TERRENO EM MEMÓRIA

    # ---------------------------------------------------------

    cc_record = cc if prefetched is not None else db.query(CostCenter).filter(CostCenter.id == cc_id).first()

    if cc_record and cc_record.manual_land_cost:

        land_cost = cc_record.manual_land_cost

        terreno += land_cost

        

        custom = cc_record.custom_data or {}

        curve_id = custom.get("land_payment_curve_id")

        start_date_str = custom.get("land_payment_start_date")

        

        import datetime as dt

        if start_date_str:

            try:

                y_str, m_str = start_date_str.split('-')

                start_month = int(m_str)

                start_year = int(y_str)

            except:

                start_month = dt.datetime.now().month

                start_year = dt.datetime.now().year

        else:

            start_month = dt.datetime.now().month

            start_year = dt.datetime.now().year

            

        if curve_id:

            from app.models.curves import StandardCurve

            curve = db.query(StandardCurve).filter(StandardCurve.id == curve_id).first()

            if curve and curve.valores_meses_json and "meses" in curve.valores_meses_json:

                percentages = [float(p) for p in curve.valores_meses_json["meses"]]

                proj_m = start_month

                proj_y = start_year

                for p in percentages:

                    val = (p / 100.0) * land_cost

                    if val > 0:

                        a_str = str(proj_y)

                        m_str = f"{proj_y}-{proj_m:02d}"

                        anual_cf_fcst[a_str]["Terreno"] += val

                        monthly_net_cf_fcst[m_str] -= val

                    

                    proj_m += 1

                    if proj_m > 12:

                        proj_m = 1

                        proj_y += 1

            else:

                a_str = str(start_year)

                m_str = f"{start_year}-{start_month:02d}"

                anual_cf_fcst[a_str]["Terreno"] += land_cost

                monthly_net_cf_fcst[m_str] -= land_cost

        else:

            a_str = str(start_year)

            m_str = f"{start_year}-{start_month:02d}"

            anual_cf_fcst[a_str]["Terreno"] += land_cost

            monthly_net_cf_fcst[m_str] -= land_cost

    # ---------------------------------------------------------



    # Montar fluxo de caixa COMBINADO: realizados + previsões (sem duplicar anos)

    # Para anos já realizados, usamos o realizado. Para anos futuros, usamos a previsão.

    anos_real = set(k for k in anual_cf_real.keys() if k != "N/A")

    anos_fcst = set(k for k in anual_cf_fcst.keys() if k != "N/A")

    all_anos = sorted(anos_real | anos_fcst)



    fluxo_caixa = []

    for ano in all_anos:

        is_previsto = ano not in anos_real  # Marca como previsto se não tiver realizado

        cf_data = anual_cf_fcst[ano] if is_previsto else anual_cf_real[ano]

        # Se o ano tem ambos (ex: ano corrente com parte realizado e parte previsto), soma os dois

        if ano in anos_real and ano in anos_fcst:

            combined = {

                "Entradas": anual_cf_real[ano]["Entradas"] + anual_cf_fcst[ano]["Entradas"],

                "Tributos": anual_cf_real[ano]["Tributos"] + anual_cf_fcst[ano]["Tributos"],

                "Terreno": anual_cf_real[ano]["Terreno"] + anual_cf_fcst[ano]["Terreno"],

                "Obras": anual_cf_real[ano]["Obras"] + anual_cf_fcst[ano]["Obras"],

                "Projetos": anual_cf_real[ano]["Projetos"] + anual_cf_fcst[ano]["Projetos"],

                "Marketing": anual_cf_real[ano]["Marketing"] + anual_cf_fcst[ano]["Marketing"],

                "Comercial": anual_cf_real[ano]["Comercial"] + anual_cf_fcst[ano]["Comercial"],

                "Administrativas": anual_cf_real[ano]["Administrativas"] + anual_cf_fcst[ano]["Administrativas"],

                "Saidas": anual_cf_real[ano]["Saidas"] + anual_cf_fcst[ano]["Saidas"],

                "Devolucao_Distratos": anual_cf_real[ano]["Devolucao_Distratos"] + anual_cf_fcst[ano]["Devolucao_Distratos"],

            }

            cf_data = combined

            is_previsto = False  # Tem realizado, não marca como puro previsto

        

        # Para saídas padrão não duplicar Terreno se for agrupado, 

        # mas na nova estrutura, Terreno é destacado.

        # Se 'Terreno' real (de Sienge) cai em 'Obras' (linha 149), 

        # precisamos garantir que o Terreno manual apareça.

        # Vamos manter Obras separado e adicionar Terreno.

        fluxo_caixa.append({

            "Ano": ano,

            "Entradas": cf_data["Entradas"],

            "Tributos": cf_data["Tributos"],

            "Terreno": cf_data["Terreno"],

            "Obras": cf_data["Obras"],

            "Projetos": cf_data["Projetos"],

            "Marketing": cf_data["Marketing"],

            "Comercial": cf_data["Comercial"],

            "Administrativas": cf_data["Administrativas"],

            "Total_Saidas": cf_data["Saidas"] + cf_data.get("Devolucao_Distratos", 0.0) + cf_data.get("Terreno", 0.0),

            "Devolucao_Distratos": cf_data.get("Devolucao_Distratos", 0.0),

            "is_forecast": is_previsto,

        })



    lucro_operacional = recebimentos - impostos - terreno - projetos - obras - adm_obra - custo_extra_obra - marketing - comercial - administrativas - despesas_extras - funding

    

    total_entradas_cf = sum(item["Entradas"] for item in fluxo_caixa)

    vgv_liquido = total_entradas_cf

    redutor_receita = impostos

    receita_liquida = vgv_liquido - redutor_receita

    custo_total = terreno + projetos + obras + adm_obra + custo_extra_obra

    margem_bruta = receita_liquida - custo_total

    margem_bruta_perc = f"{(margem_bruta / receita_liquida * 100):.2f}%" if receita_liquida > 0 else "0.00%"

    

    despesas_op = marketing + comercial + administrativas + despesas_extras + funding

    lucro_liq_operacional = margem_bruta - despesas_op

    margem_operacional_perc = f"{(lucro_liq_operacional / receita_liquida * 100):.2f}%" if receita_liquida > 0 else "0.00%"



    dre = [

        {"item": "RECEITA BRUTA", "valor": vgv_liquido, "bold": True},

        {"item": "REDUTOR DE RECEITA (Impostos)", "valor": -redutor_receita, "bold": False},

        {"item": "RECEITA LÍQUIDA", "valor": receita_liquida, "bold": True},

        {"item": "CUSTO", "valor": -custo_total, "bold": True},

        {"item": "Aquisição Área / Permuta Financeira", "valor": -terreno, "bold": False, "indent": True},

        {"item": "Projetos", "valor": -projetos, "bold": False, "indent": True},

        {"item": "Obras de Infraestrutura", "valor": -obras, "bold": False, "indent": True},

        {"item": "Administração da Obra", "valor": -adm_obra, "bold": False, "indent": True},

        {"item": "Custos Extras de Obras", "valor": -custo_extra_obra, "bold": False, "indent": True},

        {"item": "MARGEM BRUTA", "valor": margem_bruta, "bold": True},

        {"item": "Margem Bruta %", "valor": margem_bruta_perc, "is_percentage": True, "bold": True},

        {"item": "DV&A (Despesas Operacionais)", "valor": -despesas_op, "bold": True},

        {"item": "Marketing", "valor": -marketing, "bold": False, "indent": True},

        {"item": "Comercial / Comissões", "valor": -comercial, "bold": False, "indent": True},

        {"item": "Administrativas", "valor": -administrativas, "bold": False, "indent": True},

        {"item": "Despesas Extras", "valor": -despesas_extras, "bold": False, "indent": True},

        {"item": "Funding (Juros / Estruturação)", "valor": -funding, "bold": False, "indent": True},

        {"item": "LUCRO LÍQUIDO OPERACIONAL", "valor": lucro_liq_operacional, "bold": True},

        {"item": "Margem Operacional %", "valor": margem_operacional_perc, "is_percentage": True, "bold": True},

    ]



    # Cálculos Matemáticos para o Realizado (TIR, MTIR, Exposição Máxima, Payback)

    # Usa o fluxo completo (Realizado + Previsto - Estimate at Completion)

    combined_cf = defaultdict(float)

    for m, v in monthly_net_cf_real.items(): combined_cf[m] += v

    for m, v in monthly_net_cf_fcst.items(): combined_cf[m] += v

    

    cf_array = []

    final_cf_dict = {}

    sorted_cf_months = sorted([m for m in combined_cf.keys() if m != "N/A"])

    if sorted_cf_months:

        final_cf_dict = combined_cf

        first_month = sorted_cf_months[0]

        last_month = sorted_cf_months[-1]

        

        current_y, current_m = map(int, first_month.split('-'))

        end_y, end_m = map(int, last_month.split('-'))

        

        while (current_y < end_y) or (current_y == end_y and current_m <= end_m):

            m_str = f"{current_y:04d}-{current_m:02d}"

            cf_array.append(combined_cf.get(m_str, 0.0))

            

            current_m += 1

            if current_m > 12:

                current_m = 1

                current_y += 1

    else:

        # Fallback para produtos sem fluxo realizado (ex: Encerrado sem baixas importadas)

        # Usa: VGV de vendas por mês (receita real no ato da venda) + custos (saídas do fluxo)

        monthly_cf_fallback = defaultdict(float)

        

        # 1. Receitas: VGV de cada venda pelo mês do contrato (SALE transactions com data real)

        for mes, sales in sales_by_month.items():

            if mes != "N/A":

                for t in sales:

                    monthly_cf_fallback[mes] += abs(t.value)

        

        # 2. Custos: apenas valores negativos do fluxo realizado e previsto (saídas = pagamentos)

        #    Valores negativos = OUTCOME (pagamentos de obras, terreno, despesas)

        for mes, val in monthly_net_cf_real.items():

            if mes != "N/A" and val < 0:

                monthly_cf_fallback[mes] += val  # val já é negativo

        for mes, val in monthly_net_cf_fcst.items():

            if mes != "N/A" and val < 0:

                monthly_cf_fallback[mes] += val  # val já é negativo

        

        # 3. Se ainda não tiver dados, usa o fluxo combinado completo como último recurso

        if not monthly_cf_fallback:

            for mes in set(list(monthly_net_cf_real.keys()) + list(monthly_net_cf_fcst.keys())):

                if mes != "N/A":

                    monthly_cf_fallback[mes] = monthly_net_cf_real.get(mes, 0.0) + monthly_net_cf_fcst.get(mes, 0.0)

        

        final_cf_dict = dict(monthly_cf_fallback)

        sorted_fallback = sorted([m for m in monthly_cf_fallback.keys() if m != "N/A"])

        if sorted_fallback:

            first_month = sorted_fallback[0]

            last_month = sorted_fallback[-1]

            current_y, current_m = map(int, first_month.split('-'))

            end_y, end_m = map(int, last_month.split('-'))

            while (current_y < end_y) or (current_y == end_y and current_m <= end_m):

                m_str = f"{current_y:04d}-{current_m:02d}"

                cf_array.append(monthly_cf_fallback.get(m_str, 0.0))

                current_m += 1

                if current_m > 12:

                    current_m = 1

                    current_y += 1

                

    tir_mensal_final = 0.0

    tir_anual = 0.0

    mtir_mensal_final = 0.0

    mtir_anual = 0.0

    payback = 0

    exposicao_maxima = 0.0

    periodo_exposicao = 0

    vida = len(cf_array) if cf_array else 0

    

    if cf_array:

        try:

            tir_mensal = npf.irr(cf_array)

            if tir_mensal is not None and not pd.isna(tir_mensal) and tir_mensal > -1:

                tir_mensal_final = tir_mensal * 100

                tir_anual = ((1 + tir_mensal) ** 12 - 1) * 100

        except Exception:

            pass



        tma_anual = 0.12

        tma_mensal = (1 + tma_anual) ** (1/12) - 1

        try:

            mtir_mensal_val = npf.mirr(cf_array, finance_rate=tma_mensal, reinvest_rate=tma_mensal)

            if mtir_mensal_val and not pd.isna(mtir_mensal_val):

                mtir_mensal_final = mtir_mensal_val * 100

                mtir_anual = ((1 + mtir_mensal_val) ** 12 - 1) * 100

        except Exception:

            pass

            

        acum = 0

        caixa_acum_list = []

        for cf in cf_array:

            acum += cf

            caixa_acum_list.append(acum)

            if acum < exposicao_maxima:

                exposicao_maxima = acum

                

        exposicao_idx = -1

        for i, val in enumerate(caixa_acum_list):

            if val == exposicao_maxima:

                exposicao_idx = i

                break

                

        periodo_exposicao = exposicao_idx + 1 if exposicao_idx >= 0 else 0

        

        for i in range(max(0, periodo_exposicao - 1), len(caixa_acum_list)):

            if caixa_acum_list[i] >= 0:

                payback = i + 1

                break



    rent_inv = (lucro_operacional / vgv_vendido) * 100 if vgv_vendido > 0 else 0.0

    if kpis_only:
        return {
            "vgv_vendido": vgv_vendido,
            "distratos": distratos,
            "vgv_estoque": vgv_estoque,
            "lucro_operacional": lucro_operacional,
            "lucro_liq_operacional": lucro_liq_operacional,
            "receita_bruta": vgv_liquido,
            "final_cf_dict": final_cf_dict,
            "monthly_net_cf_real": monthly_net_cf_real,
            "monthly_net_cf_fcst": monthly_net_cf_fcst,
            "monthly_revenues_real": monthly_revenues_real,
            "monthly_revenues_fcst": monthly_revenues_fcst,
            "dre": dre,
            "fluxo_caixa": fluxo_caixa,
            "tir_anual": tir_anual,
            "tir_mensal": tir_mensal_final,
            "mtir_anual": mtir_anual,
            "mtir_mensal": mtir_mensal_final,
            "payback": payback,
            "periodo_exposicao": periodo_exposicao,
            "vida": vida,
            "exposicao_maxima": exposicao_maxima,
            "rent_inv": rent_inv,
            "estoque_unidades": len(available_units),
        }

    # Calcular Velocidade de Vendas (VSO)

    total_units = db.query(Unit).filter(Unit.cost_center_id == cc_id).count()

    all_sales_months = set(sales_by_month.keys()) | set(distratos_by_month.keys())

    if "N/A" in all_sales_months:

        all_sales_months.remove("N/A")

    sorted_all_months = sorted(list(all_sales_months))

    

    anos_dict = defaultdict(lambda: {"vendas": 0, "distratos": 0, "meses": []})

    saldo_acumulado = 0

    estoque_inicial_acumulado = total_units

    

    total_vendas = sum(len(sales_by_month[m]) for m in sales_by_month if m != "N/A")

    total_distratos_count = sum(len(distratos_by_month[m]) for m in distratos_by_month if m != "N/A")

    total_saldo_final = total_vendas - total_distratos_count



    for m in sorted_all_months:

        ano, mes_str = m.split('-')

        v = len(sales_by_month[m])

        d = len(distratos_by_month[m])

        saldo_mes = v - d

        

        vso_mes = (v / total_units) * 100 if total_units > 0 else 0

        perc = (saldo_mes / total_saldo_final) * 100 if total_saldo_final > 0 else 0

        

        anos_dict[ano]["vendas"] += v

        anos_dict[ano]["distratos"] += d

        anos_dict[ano]["meses"].append({

            "mes": m,

            "vendas": v,

            "distratos": d,

            "saldo": saldo_mes,

            "perc": round(perc, 2),

            "vel": round(vso_mes, 2)

        })

        

    velocidade_vendas_list = []

    

    for ano in sorted(anos_dict.keys()):

        v = anos_dict[ano]["vendas"]

        d = anos_dict[ano]["distratos"]

        saldo_ano = v - d

        

        # Velocidade de Vendas do ano: Vendas brutas do ano / Total de Unidades * 100

        vel_ano = (v / total_units) * 100 if total_units > 0 else 0

        

        # % sobre total vendido: Saldo líquido do ano / Total Saldo de todos os anos

        perc_ano = (saldo_ano / total_saldo_final) * 100 if total_saldo_final > 0 else 0

        

        # Reordenar os meses do mais antigo para mais novo

        meses_sorted = sorted(anos_dict[ano]["meses"], key=lambda x: x["mes"])

        

        velocidade_vendas_list.append({

            "ano": ano,

            "vendas": v,

            "distratos": d,

            "saldo": saldo_ano,

            "perc": round(perc_ano, 2),

            "vel": round(vel_ano, 2),

            "meses": meses_sorted

        })

    # A lista já está do mais antigo para o mais novo devido ao sorted(anos_dict.keys())



    # Calcular Planos Contratados (VGV Vendido + Distratos)

    sales_transactions = db.query(ActualTransaction).filter(

        ActualTransaction.cost_center_id == cc_id,

        ActualTransaction.transaction_type == "SALE",

        ActualTransaction.category.in_(["VGV Vendido", "Distrato"])

    ).all()

    

    bins_val = {'Até 6X': 0.0, 'Até 12x': 0.0, 'Até 24x': 0.0, 'Até 36x': 0.0, 'Até 48x': 0.0, 'Até 60x': 0.0, 'Até 120x': 0.0, 'Até 156x': 0.0, 'Até 180x': 0.0}

    

    for t in sales_transactions:

        inst = t.installments_number or 0

        val = abs(t.value)

        if inst <= 6: bins_val['Até 6X'] += val

        elif inst <= 12: bins_val['Até 12x'] += val

        elif inst <= 24: bins_val['Até 24x'] += val

        elif inst <= 36: bins_val['Até 36x'] += val

        elif inst <= 48: bins_val['Até 48x'] += val

        elif inst <= 60: bins_val['Até 60x'] += val

        elif inst <= 120: bins_val['Até 120x'] += val

        elif inst <= 156: bins_val['Até 156x'] += val

        else: bins_val['Até 180x'] += val



    total_planos = sum(bins_val.values())

    distribuicao = []

    val_curto = 0.0

    val_longo = 0.0

    

    for k, v in bins_val.items():

        perc = (v / total_planos * 100) if total_planos > 0 else 0

        if k in ['Até 6X', 'Até 12x', 'Até 24x', 'Até 36x', 'Até 48x']:

            val_curto += v

            distribuicao.append({"name": k, "curto": round(perc, 1), "longo": 0})

        else:

            val_longo += v

            distribuicao.append({"name": k, "curto": 0, "longo": round(perc, 1)})

            

    perc_curto = (val_curto / total_planos * 100) if total_planos > 0 else 0

    perc_longo = (val_longo / total_planos * 100) if total_planos > 0 else 0

    

    planos_vendas = {

        "curto_longo": [

            {"name": "Plano Curto", "value": round(perc_curto, 1), "color": "#0F5B30"},

            {"name": "Plano Longo", "value": round(perc_longo, 1), "color": "#94a3b8"}

        ],

        "distribuicao": distribuicao

    }



    return {

        "vgv_vendido": vgv_vendido,

        "distratos": distratos,

        "recebimentos": recebimentos,

        "saidas_totais": impostos + terreno + projetos + obras + adm_obra + custo_extra_obra + marketing + comercial + administrativas + despesas_extras + funding,

        "vgv_estoque": vgv_estoque,

        "estoque_area": available_area,

        "estoque_unidades": len(available_units),

        "preco_medio": avg_price,

        "dre": dre,

        "fluxo_caixa": fluxo_caixa,

        "lucro_operacional": lucro_operacional,

        "velocidade_vendas": velocidade_vendas_list,

        "tir_anual": tir_anual,

        "tir_mensal": tir_mensal_final,

        "mtir_anual": mtir_anual,

        "mtir_mensal": mtir_mensal_final,

        "payback": payback,

        "periodo_exposicao": periodo_exposicao,

        "vida": vida,

        "exposicao_maxima": exposicao_maxima,

        "rent_inv": rent_inv,

        "planos_vendas": planos_vendas,

        "total_units": total_units,

        "total_sold": total_vendas,

        "total_returned": total_distratos_count,

        "total_balance": total_saldo_final,

        "fluxo_caixa": fluxo_caixa,

        "dre": dre,

        "monthly_net_cf_real": monthly_net_cf_real,

        "monthly_net_cf_fcst": monthly_net_cf_fcst,

        "monthly_revenues_real": monthly_revenues_real,

        "monthly_revenues_fcst": monthly_revenues_fcst,

        "receita_bruta": vgv_liquido,

        "lucro_liq_operacional": lucro_liq_operacional,

        "final_cf_dict": final_cf_dict

    }



def _calculate_financial_indicators(cf_dict):

    tir_anual = None

    tir_mensal_final = None

    mtir_anual = None

    mtir_mensal_final = None

    payback = None

    exposicao_maxima = 0.0

    periodo_exposicao = 0



    sorted_months = sorted([k for k in cf_dict.keys() if k != "N/A"])

    cf_array = []

    if sorted_months:

        first_month = sorted_months[0]

        last_month = sorted_months[-1]

        current_y, current_m = map(int, first_month.split('-'))

        end_y, end_m = map(int, last_month.split('-'))

        

        while (current_y < end_y) or (current_y == end_y and current_m <= end_m):

            m_str = f"{current_y:04d}-{current_m:02d}"

            cf_array.append(cf_dict.get(m_str, 0.0))

            current_m += 1

            if current_m > 12:

                current_m = 1

                current_y += 1

                

    vida = len(cf_array) if cf_array else 0

    

    if cf_array:

        try:

            tir_mensal = npf.irr(cf_array)

            if tir_mensal is not None and not pd.isna(tir_mensal) and tir_mensal > -1:

                tir_mensal_final = tir_mensal * 100

                tir_anual = ((1 + tir_mensal) ** 12 - 1) * 100

        except Exception:

            pass



        tma_anual = 0.12

        tma_mensal = (1 + tma_anual) ** (1/12) - 1

        try:

            mtir_mensal_val = npf.mirr(cf_array, finance_rate=tma_mensal, reinvest_rate=tma_mensal)

            if mtir_mensal_val and not pd.isna(mtir_mensal_val):

                mtir_mensal_final = mtir_mensal_val * 100

                mtir_anual = ((1 + mtir_mensal_val) ** 12 - 1) * 100

        except Exception:

            pass

            

        acum = 0

        caixa_acum_list = []

        for cf in cf_array:

            acum += cf

            caixa_acum_list.append(acum)

            if acum < exposicao_maxima:

                exposicao_maxima = acum

                

        exposicao_idx = -1

        for i, val in enumerate(caixa_acum_list):

            if val == exposicao_maxima:

                exposicao_idx = i

                break

                

        periodo_exposicao = exposicao_idx + 1 if exposicao_idx >= 0 else 0

        

        for i in range(max(0, periodo_exposicao - 1), len(caixa_acum_list)):

            if caixa_acum_list[i] >= 0:

                payback = i + 1

                break

                

    return {

        "tir_anual": tir_anual,

        "tir_mensal": tir_mensal_final,

        "mtir_anual": mtir_anual,

        "mtir_mensal": mtir_mensal_final,

        "payback": payback,

        "exposicao_maxima": exposicao_maxima,

        "periodo_exposicao": periodo_exposicao,

        "vida": vida

    }



def _calc_slice_actuals(db, macro_prefix, native_cc_id, pct, view_mode, cached_cat_to_group, actuals_cache=None, prefetched=None, kpis_only: bool = False):

    native_cc = db.query(CostCenter).filter(CostCenter.id == native_cc_id).first()

    city, proj_name = parse_project_name(native_cc)

    

    # Busca todos do mesmo prefixo 3-digits (ex: 143)

    base_prefix = native_cc.id_sienge[:3] if native_cc.id_sienge and len(native_cc.id_sienge) >= 3 else str(native_cc.id)

    all_ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{base_prefix}%")).all()

    

    macro_monthly_cf = defaultdict(float)

    macro_monthly_rev = defaultdict(float)

    macro_vgv_vendido = 0.0

    macro_distratos = 0.0

    macro_lucro_operacional = 0.0

    macro_receita_bruta = 0.0

    macro_lucro_liq_operacional = 0.0

    

    macro_fc = defaultdict(lambda: defaultdict(float))

    macro_dre = defaultdict(lambda: defaultdict(float))

    

    # 1. Agrega o Macro

    for sub_cc in all_ccs:

        if actuals_cache is not None and sub_cc.id in actuals_cache:
            act = actuals_cache[sub_cc.id]
        else:
            act = _calc_actuals_for_cc(db, sub_cc.id, None, 1.0, 1.0, cached_cat_to_group, prefetched=prefetched, kpis_only=kpis_only)
            if actuals_cache is not None:
                actuals_cache[sub_cc.id] = act

        macro_vgv_vendido += act.get("vgv_vendido", 0.0)

        macro_distratos += act.get("distratos", 0.0)

        macro_lucro_operacional += act.get("lucro_operacional", 0.0)

        macro_receita_bruta += act.get("receita_bruta", 0.0)

        macro_lucro_liq_operacional += act.get("lucro_liq_operacional", 0.0)

        

        for m, v in act.get("monthly_net_cf_real", {}).items(): macro_monthly_cf[m] += v

        for m, v in act.get("monthly_net_cf_fcst", {}).items(): macro_monthly_cf[m] += v

        for m, v in act.get("monthly_revenues_real", {}).items(): macro_monthly_rev[m] += v

        for m, v in act.get("monthly_revenues_fcst", {}).items(): macro_monthly_rev[m] += v

            

        for row in act.get("fluxo_caixa", []):

            ano = row.get("ano", row.get("Ano"))

            macro_fc[ano]["is_forecast"] = macro_fc[ano].get("is_forecast", False) or row.get("is_forecast", False)

            for k in ["Entradas", "Devolucao_Distratos", "Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas", "Saidas"]:

                macro_fc[ano][k] += row.get(k, 0.0)

                

        for row in act.get("dre", []):

            if row.get("is_percentage"): continue

            item = row["item"]

            macro_dre[item]["valor"] += row["valor"]

            macro_dre[item]["bold"] = row.get("bold", False)

            macro_dre[item]["indent"] = row.get("indent", False)

            

    # 2. Agrega o Nativo

    if actuals_cache is not None and native_cc_id in actuals_cache:
        native_act = actuals_cache[native_cc_id]
    else:
        native_act = _calc_actuals_for_cc(db, native_cc_id, None, 1.0, 1.0, cached_cat_to_group, prefetched=prefetched, kpis_only=kpis_only)
        if actuals_cache is not None:
            actuals_cache[native_cc_id] = native_act

    

    # 3. Constroi Fluxo Mensal

    slice_monthly_cf = defaultdict(float)

    all_months = set(macro_monthly_cf.keys()) | set(native_act.get("monthly_net_cf_real", {}).keys()) | set(native_act.get("monthly_net_cf_fcst", {}).keys())

    for m in all_months:

        if m == "N/A": continue

        m_rev = macro_monthly_rev.get(m, 0.0)

        m_cf = macro_monthly_cf.get(m, 0.0)

        m_costs = m_rev - m_cf

        m_slice_costs = m_costs * pct

        

        m_native_rev = native_act.get("monthly_revenues_real", {}).get(m, 0.0) + native_act.get("monthly_revenues_fcst", {}).get(m, 0.0)

        slice_monthly_cf[m] = m_native_rev - m_slice_costs

        

    c = db.query(CostCenter).filter(CostCenter.id == native_cc_id).first()

    mlc = 0.0

    first_m = None

    if c and c.manual_land_cost and float(c.manual_land_cost) > 0:

        mlc = float(c.manual_land_cost)

        sorted_m = sorted([m for m in slice_monthly_cf.keys() if m != "N/A"])

        first_m = sorted_m[0] if sorted_m else (datetime.now().strftime("%Y-%m"))

        slice_monthly_cf[first_m] -= mlc

        

    ind = _calculate_financial_indicators(slice_monthly_cf)

    

    # 4. Result dict

    macro_revenues = macro_vgv_vendido - macro_distratos

    macro_costs = macro_revenues - macro_lucro_operacional

    slice_costs = macro_costs * pct

    lucro = (native_act.get("vgv_vendido", 0.0) - native_act.get("distratos", 0.0)) - slice_costs - mlc

    

    slice_act = native_act.copy()

    slice_act["lucro_operacional"] = lucro

    slice_act["tir_anual"] = ind.get("tir_anual") or 0.0

    slice_act["tir_mensal"] = ind.get("tir_mensal") or 0.0

    slice_act["mtir_anual"] = ind.get("mtir_anual") or 0.0

    slice_act["mtir_mensal"] = ind.get("mtir_mensal") or 0.0

    slice_act["payback"] = ind.get("payback") or 0

    slice_act["exposicao_maxima"] = ind.get("exposicao_maxima") or 0.0

    slice_act["periodo_exposicao"] = ind.get("periodo_exposicao") or 0

    slice_act["vida"] = ind.get("vida") or 0

    

    # 5. DRE

    new_dre = []

    dre_order = ["RECEITA BRUTA", "Distratos / Cancelamentos", "Tributos Incidentes / Vendas", "RECEITA LÍQUIDA", "Margem Bruta", "CUSTOS DIRETOS DA CONSTRUÇÃO (Custo + Terreno)", "Terreno (Físico ou Permuta)", "Projetos", "Obras", "Administração de Obra", "Custo Extra Obra", "MARGEM BRUTA", "DV&A (Despesas Operacionais)", "Marketing", "Comercial / Comissões", "Administrativas", "Despesas Extras", "Funding (Juros / Estruturação)", "LUCRO LÍQUIDO OPERACIONAL"]

    for item in dre_order:

        m_row = macro_dre.get(item, {})

        n_row = next((r for r in native_act.get("dre", []) if r["item"] == item), {})

        

        if "RECEITA" in item.upper() or "DISTRATO" in item.upper():

            val = n_row.get("valor", 0.0)

        else:

            val = m_row.get("valor", 0.0) * pct

            

        new_dre.append({"item": item, "valor": val, "bold": m_row.get("bold", n_row.get("bold", False)), "indent": m_row.get("indent", n_row.get("indent", False))})

        

    receita_liquida = next((r["valor"] for r in new_dre if r["item"] == "RECEITA LÍQUIDA"), 0.0)

    

    if mlc > 0:

        for r in new_dre:

            if r["item"] == "Terreno (Físico ou Permuta)":

                r["valor"] += mlc

            elif r["item"] == "CUSTOS DIRETOS DA CONSTRUÇÃO (Custo + Terreno)":

                r["valor"] += mlc

        custo_direto = next((r["valor"] for r in new_dre if r["item"] == "CUSTOS DIRETOS DA CONSTRUÇÃO (Custo + Terreno)"), 0.0)

        margem_bruta = receita_liquida - custo_direto

        for r in new_dre:

            if r["item"] == "MARGEM BRUTA":

                r["valor"] = margem_bruta

            elif r["item"] == "LUCRO LÍQUIDO OPERACIONAL":

                r["valor"] -= mlc



    margem_bruta = next((r["valor"] for r in new_dre if r["item"] == "MARGEM BRUTA"), 0.0)

    lucro_liq_operacional = next((r["valor"] for r in new_dre if r["item"] == "LUCRO LÍQUIDO OPERACIONAL"), 0.0)

    

    new_dre.insert(4, {"item": "Margem Bruta %", "valor": (margem_bruta / receita_liquida * 100) if receita_liquida > 0 else 0.0, "is_percentage": True, "bold": True})

    new_dre.append({"item": "Margem Operacional %", "valor": (lucro_liq_operacional / receita_liquida * 100) if receita_liquida > 0 else 0.0, "is_percentage": True, "bold": True})

    slice_act["dre"] = new_dre

    

    # 6. Fluxo Anual

    new_fc = []

    all_years = sorted(set(list(macro_fc.keys()) + [r.get("ano", r.get("Ano")) for r in native_act.get("fluxo_caixa", [])]))

    for ano in all_years:

        if ano == "N/A": continue

        m_row = macro_fc.get(ano, defaultdict(float))

        n_row = next((r for r in native_act.get("fluxo_caixa", []) if r.get("ano", r.get("Ano")) == ano), defaultdict(float))

        

        row = {"ano": ano, "Ano": ano, "is_forecast": m_row.get("is_forecast", False)}

        for k in ["Entradas", "Devolucao_Distratos", "Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas", "Saidas"]:

            if k in ["Entradas", "Devolucao_Distratos"]:

                row[k] = n_row.get(k, 0.0)

            else:

                row[k] = m_row.get(k, 0.0) * pct

        

        row["Total_Saidas"] = row.get("Saidas", 0) + row.get("Devolucao_Distratos", 0)

        if mlc > 0 and first_m and first_m[:4] == ano:

            row["Terreno"] += mlc

            row["Saidas"] += mlc

            row["Total_Saidas"] += mlc

        row["Saldo_Mes"] = row.get("Entradas", 0) - row.get("Total_Saidas", 0)

        new_fc.append(row)

        

    slice_act["fluxo_caixa"] = new_fc

    return slice_act



def parse_project_name(cc_obj):

    custom = cc_obj.custom_data or {}

    city = custom.get("__cidade_sienge") or "Centro de Custo"

    project_name = cc_obj.nome or ""

    if "frota" in project_name.lower():

        city = "FROTA"

        project_name = "FROTA"

    elif " - " in project_name:

        parts = project_name.split(" - ", 1)

        city = parts[0].strip()

        project_name = parts[1].strip()

    project_name = project_name.replace(" - PARCERIA GAP", "").replace(" - PARCERIA", "").replace(" - MLDU", "").strip()

    return city, project_name


def _kpis_do_consolidado(acts):
    """Mesmos indicadores da visão consolidada do detalhe, somando os centros do grupo."""
    vgv_vendido = 0.0
    vgv_estoque = 0.0
    distratos = 0.0
    lucro = 0.0
    combined_cf = defaultdict(float)
    for act in acts:
        vgv_vendido += act.get("vgv_vendido", 0.0) or 0.0
        vgv_estoque += act.get("vgv_estoque", 0.0) or 0.0
        distratos += act.get("distratos", 0.0) or 0.0
        lucro += act.get("lucro_liq_operacional", 0.0) or 0.0
        for mes, val in (act.get("final_cf_dict") or {}).items():
            combined_cf[mes] += val
    indicators = _calculate_financial_indicators(combined_cf or {0: 0.0})
    vendas_ativas = vgv_vendido - distratos
    vgv_total = vendas_ativas + vgv_estoque
    exposicao = indicators.get("exposicao_maxima") or 0.0
    return {
        "vgv_total": vgv_total,
        "vendas_acumuladas": vendas_ativas,
        "perc_vendido": (vendas_ativas / vgv_total * 100) if vgv_total > 0 else 0.0,
        "lucro": lucro,
        "tir_anual": indicators.get("tir_anual") or 0.0,
        "mtir_anual": indicators.get("mtir_anual") or 0.0,
        "payback": indicators.get("payback") or 0,
        "exposicao_max_caixa": exposicao,
        "exposicao_caixa_vgv": (abs(exposicao) / vgv_total * 100) if vgv_total > 0 else 0.0,
        "vso": 0.0,
        "distrato_venda": (distratos / vgv_vendido * 100) if vgv_vendido > 0 else 0.0,
    }


def _kpis_da_fatia(slice_act):
    """Mesmos campos que o detalhe devolve para um centro com rateio."""
    vendas_ativas = (slice_act.get("vgv_vendido", 0.0) or 0.0) - (slice_act.get("distratos", 0.0) or 0.0)
    vgv_total = vendas_ativas + (slice_act.get("vgv_estoque", 0.0) or 0.0)
    exposicao = slice_act.get("exposicao_maxima") or 0.0
    vgv_vendido = slice_act.get("vgv_vendido", 0.0) or 0.0
    return {
        "vgv_total": vgv_total,
        "vendas_acumuladas": vendas_ativas,
        "perc_vendido": (vendas_ativas / vgv_total * 100) if vgv_total > 0 else 0.0,
        "lucro": slice_act.get("lucro_liq_operacional", 0.0) or 0.0,
        "tir_anual": slice_act.get("tir_anual", 0.0) or 0.0,
        "mtir_anual": slice_act.get("mtir_anual", 0.0) or 0.0,
        "payback": slice_act.get("payback", 0) or 0,
        "exposicao_max_caixa": exposicao,
        "exposicao_caixa_vgv": (abs(exposicao) / vgv_total * 100) if vgv_total > 0 else 0.0,
        "vso": 0.0,
        "distrato_venda": ((slice_act.get("distratos", 0.0) or 0.0) / vgv_vendido * 100) if vgv_vendido > 0 else 0.0,
    }


@router.get("/summary")

def get_tracking_summary(db: Session = Depends(get_db), current_user: UserResponse = Depends(deps.get_current_active_user)):

    """

    Consolida as Viabilidades Aprovadas e os Centros de Custo rastreados

    para exibir no Painel Corporativo de Empreendimentos.

    """

    results_list = []

    

    # 1. Buscar todas as Viabilidades Oficiais

    viabilities = db.query(Viability).filter(

        Viability.version_of_id == None,

        Viability.status.notin_(["Em Andamento", "Em Aprovação"])

    ).all()

    

    viab_dict = {v.id: v for v in viabilities}

    

    # Processar Viabilidades Puras (ex: Land Bank)

    for v in viabilities:

        phase = v.phases[0] if v.phases else None

        calc = {}

        if phase:

            try:

                res = calculate_viability_results(db, phase.id)

                if "indicators" in res:

                    calc = res["indicators"]

            except Exception:

                pass

                

        cat = "Land Bank"

        if v.status in ["Em Obras", "Lançado"]: cat = "Em Andamento"

        elif v.status in ["Concluído", "Encerrado"]: cat = "Encerrado"

            

        results_list.append({

            "id": f"v-{v.id}",

            "db_id": v.id,

            "itemType": "viability",

            "project_name": v.project_name,

            "category": cat,

            "status": v.status,

            "city": v.city or "Não informado", 

            "vgv_total": calc.get("vgv_total", 0.0),

            "vendas_acumuladas": 0.0, 

            "perc_vendido": 0.0,

            "lucro": calc.get("lucro_liquido", 0.0),

            "tir_anual": calc.get("tir_aa", 0.0),

            "mtir_anual": calc.get("mtir_aa", 0.0),

            "payback_anos": calc.get("payback", 0.0),

            "exposicao_max_caixa": calc.get("exposicao_maxima") or 0.0,

            "exposicao_caixa_vgv": (abs(calc.get("exposicao_maxima") or 0.0) / calc.get("vgv_total", 1.0)) * 100 if calc.get("vgv_total") else 0.0,

            "vso": 0.0,

            "distrato_venda": 0.0

        })



    # 2. Buscar Centros de Custo Trackeados

    tracked_cost_centers = db.query(CostCenter).filter(CostCenter.track_in_dashboard == True).all()

    

    from collections import defaultdict

    cc_groups = defaultdict(list)

    slices = []

    

    # Pré-carregar o mapeamento de DRE

    from app.models.vision import Vision, FinancialPlanVisionLink

    from app.models.financial_plan import FinancialPlan

    cached_cat_to_group = {}

    vision = db.query(Vision).filter_by(is_padrao=True).first()

    if not vision: vision = db.query(Vision).first()

    if vision:
        node_map = {n.id: n.descricao.strip().upper() for n in vision.nodes if n.descricao}
        if node_map:
            links = db.query(FinancialPlanVisionLink, FinancialPlan).join(
                FinancialPlan, FinancialPlan.id == FinancialPlanVisionLink.financial_plan_id
            ).filter(
                FinancialPlanVisionLink.vision_node_id.in_(node_map.keys())
            ).all()
            for link, fp in links:
                if fp:
                    cached_cat_to_group[fp.name.strip().lower()] = node_map[link.vision_node_id]



    for c in tracked_cost_centers:

        macro_prefix = c.id_sienge[:3] if c.id_sienge and len(c.id_sienge) >= 3 else str(c.id)

        

        # Verifica se este centro de custo é um "Slice" (Produto com rateio próprio)

        slice_pct = None

        if c.apportionment_rules:

            for rule in c.apportionment_rules:

                if str(rule.get("project_prefix")) == str(c.id) or str(rule.get("project_prefix")) == str(getattr(c, "id_sienge", "")) or str(rule.get("viability_id")) == str(c.id):

                    slice_pct = float(rule.get("percentage") or 0) / 100.0

                    break

        

        if slice_pct is not None:

            slices.append({"cc": c, "macro_prefix": macro_prefix, "pct": slice_pct})

        else:

            city, proj_name = parse_project_name(c)

            group_key = f"{macro_prefix}_{proj_name}"

            

            if group_key not in cc_groups:

                members = []

                if c.id_sienge and len(c.id_sienge) >= 3:

                    related_ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{macro_prefix}%")).all()

                    # Garante que só puxa centros de custo do mesmo projeto real

                    for rc in related_ccs:

                        if parse_project_name(rc)[1] == proj_name:

                            members.append(rc)

                if not any(rc.id == c.id for rc in members):

                    members.append(c)

                cc_groups[group_key] = members

    





    needed_ids = {sub_cc.id for members in cc_groups.values() for sub_cc in members}
    for sl in slices:
        needed_ids.add(sl["cc"].id)
        for (cid,) in db.query(CostCenter.id).filter(CostCenter.id_sienge.like(f"{sl['macro_prefix']}%")).all():
            needed_ids.add(cid)
    prefetched = _prefetch_tracking_actuals(db, needed_ids)

    cached_actuals = {}

    def get_actuals(cc_id):

        if cc_id not in cached_actuals:

            cached_actuals[cc_id] = _calc_actuals_for_cc(
                db, cc_id, cached_cat_to_group=cached_cat_to_group, prefetched=prefetched, kpis_only=True
            )

        return cached_actuals[cc_id]



    # Processa os grupos normais (Mesclados) e Slices reutilizando a lógica
    for base_class, ccs in cc_groups.items():
        main_cc = sorted(ccs, key=lambda x: len(x.nome or ""))[0]
        city, project_name = parse_project_name(main_cc)
        
        cat = "Em Andamento"
        if main_cc.project_phase in ["Encerrado", "Concluído"]: cat = "Encerrado"
        
        raw_id = f"cg-{base_class}"
        kpis = {}
        try:
            kpis = _kpis_do_consolidado([get_actuals(sub_cc.id) for sub_cc in ccs])
        except Exception as e:
            print(f"Error calculating details for {raw_id}: {e}")
        results_list.append({
            "id": raw_id,
            "db_id": base_class,
            "itemType": "cost_center",
            "project_name": project_name,
            "category": cat,
            "status": "Em comercialização" if main_cc.project_phase == "Em Andamento" else main_cc.project_phase,
            "city": city,
            "vgv_total": kpis.get("vgv_total", 0.0),
            "vendas_acumuladas": kpis.get("vendas_acumuladas", 0.0),
            "perc_vendido": kpis.get("perc_vendido", 0.0),
            "lucro": kpis.get("lucro", 0.0) if "lucro" in kpis else kpis.get("lucro_operacional", 0.0),
            "tir_anual": kpis.get("tir_anual", 0.0),
            "mtir_anual": kpis.get("mtir_anual", 0.0),
            "payback_anos": kpis.get("payback", 0.0),
            "exposicao_max_caixa": kpis.get("exposicao_max_caixa", 0.0),
            "exposicao_caixa_vgv": kpis.get("exposicao_caixa_vgv", 0.0),
            "vso": kpis.get("vso", 0.0),
            "distrato_venda": kpis.get("distrato_venda", 0.0)
        })

    # Processa os Slices
    for sl in slices:
        c = sl["cc"]
        macro_prefix = sl["macro_prefix"]
        pct = sl["pct"]
        city, project_name = parse_project_name(c)
        cat = "Em Andamento"
        if c.project_phase in ["Encerrado", "Concluído"]: cat = "Encerrado"
        
        raw_id = f"cg-{macro_prefix}_slice_{c.id}"
        kpis = {}
        try:
            slice_act = _calc_slice_actuals(
                db, macro_prefix, c.id, pct, "consolidado", cached_cat_to_group,
                cached_actuals, prefetched=prefetched, kpis_only=True,
            )
            kpis = _kpis_da_fatia(slice_act)
        except Exception as e:
            print(f"Error calculating details for slice {raw_id}: {e}")
        results_list.append({
            "id": raw_id,
            "db_id": c.id,
            "itemType": "cost_center",
            "project_name": project_name,
            "category": cat,
            "status": "Em comercialização" if c.project_phase == "Em Andamento" else c.project_phase,
            "city": city,
            "vgv_total": kpis.get("vgv_total", 0.0),
            "vendas_acumuladas": kpis.get("vendas_acumuladas", 0.0),
            "perc_vendido": kpis.get("perc_vendido", 0.0),
            "lucro": kpis.get("lucro", 0.0) if "lucro" in kpis else kpis.get("lucro_operacional", 0.0),
            "tir_anual": kpis.get("tir_anual", 0.0),
            "mtir_anual": kpis.get("mtir_anual", 0.0),
            "payback_anos": kpis.get("payback", 0.0),
            "exposicao_max_caixa": kpis.get("exposicao_max_caixa", 0.0),
            "exposicao_caixa_vgv": kpis.get("exposicao_caixa_vgv", 0.0),
            "vso": kpis.get("vso", 0.0),
            "distrato_venda": kpis.get("distrato_venda", 0.0)
        })


    # Buscar timestamp da última execução do sync das APIs (gravado pelo scheduler/sync)

    from app.models.system_settings import SystemSettings

    last_sync_at = None

    try:

        setting = db.query(SystemSettings).filter_by(key="last_api_sync").first()

        if setting and setting.value:

            last_sync_at = setting.value.get("timestamp") if isinstance(setting.value, dict) else str(setting.value)

    except Exception:

        pass



    return {"items": results_list, "last_sync_at": last_sync_at}




@router.get("/{id}/details")
def get_tracking_details(id: str, view_mode: str = 'consolidado', db: Session = Depends(get_db), current_user: UserResponse = Depends(deps.get_current_active_user)):
    return _get_tracking_details_logic(db, id, view_mode)

def _get_tracking_details_logic(db, id: str, view_mode: str = 'consolidado'):

    """

    Retorna os dados detalhados (DRE Sintética e Fluxo de Caixa Anualizado)

    para o Painel Corporativo. O ID tem formato 'v-1' ou 'cg-142'.

    """

    if not id or "-" not in id:

        raise HTTPException(status_code=400, detail="ID inválido.")

        

    item_type, raw_id = id.split("-", 1)



    try:

        db_id = int(raw_id)

    except ValueError:

        db_id = 0 # Fallback

    

    if item_type == "cg":

        is_slice = "_slice_" in raw_id

        if is_slice:

            macro_prefix, cc_id = raw_id.split("_slice_")

            native_cc = db.query(CostCenter).filter(CostCenter.id_sienge == cc_id).first()

            if not native_cc:

                try:

                    native_cc = db.query(CostCenter).filter(CostCenter.id == int(cc_id)).first()

                except:

                    pass

            ccs = [native_cc] if native_cc else []

        else:

            # Pode vir como "141_PARQUE CIDADE" ou apenas "141"

            if "_" in raw_id and not raw_id.startswith("_"):

                parts = raw_id.split("_", 1)

                macro_prefix = parts[0]

                proj_name_filter = parts[1]

            else:

                macro_prefix = raw_id

                proj_name_filter = None

                

            raw_ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{macro_prefix}%")).all()

            if proj_name_filter:

                ccs = [c for c in raw_ccs if parse_project_name(c)[1] == proj_name_filter]

            else:

                ccs = raw_ccs

            

        if not ccs:

            raise HTTPException(status_code=404, detail="Centro de Custo não encontrado.")

            

        main_cc = sorted(ccs, key=lambda x: len(x.nome or ""))[0]

        

        # Consolida tudo

        combined_actuals = {

            "vgv_vendido": 0.0, "vgv_estoque": 0.0, "estoque_unidades": 0,

            "distratos": 0.0, "lucro_operacional": 0.0, "lucro_liq_operacional": 0.0, "receita_bruta": 0.0, "tir_anual": 0.0, "tir_mensal": 0.0,

            "mtir_anual": 0.0, "mtir_mensal": 0.0, "payback": 0, "exposicao_maxima": 0.0, "rent_inv": 0.0,

            "periodo_exposicao": 0, "vida": 0,

            "total_units": 0, "total_sold": 0, "total_returned": 0, "total_balance": 0

        }

        

        combined_dre = {}

        combined_fc = {}

        combined_planos_bins = {'Até 6X': 0.0, 'Até 12x': 0.0, 'Até 24x': 0.0, 'Até 36x': 0.0, 'Até 48x': 0.0, 'Até 60x': 0.0, 'Até 120x': 0.0, 'Até 156x': 0.0, 'Até 180x': 0.0}

        combined_vel_anos = defaultdict(lambda: {"vendas": 0, "distratos": 0, "meses_dict": defaultdict(lambda: {"vendas": 0, "distratos": 0})})

        

        

        from app.models.partnership import PartnershipConfig

        from app.models.vision import Vision, FinancialPlanVisionLink

        from app.models.financial_plan import FinancialPlan

        

        cached_cat_to_group = {}

        vision = db.query(Vision).filter_by(is_padrao=True).first()

        if not vision:

            vision = db.query(Vision).first()

        if vision:
            node_map = {n.id: n.descricao.strip().upper() for n in vision.nodes if n.descricao}
            if node_map:
                links = db.query(FinancialPlanVisionLink, FinancialPlan).join(
                    FinancialPlan, FinancialPlan.id == FinancialPlanVisionLink.financial_plan_id
                ).filter(
                    FinancialPlanVisionLink.vision_node_id.in_(node_map.keys())
                ).all()
                for link, fp in links:
                    if fp:
                        cached_cat_to_group[fp.name.strip().lower()] = node_map[link.vision_node_id]

        

        if is_slice:

            try:

                cc_id_int = int(cc_id)

            except:

                cc_id_int = -1

            native_cc = db.query(CostCenter).filter(or_(CostCenter.id_sienge == cc_id, CostCenter.id == cc_id_int)).first()

            if native_cc:

                pct = 1.0

                if native_cc.apportionment_rules:

                    for rule in native_cc.apportionment_rules:

                        if str(rule.get("project_prefix")) == str(native_cc.id) or str(rule.get("project_prefix")) == str(getattr(native_cc, "id_sienge", "")) or str(rule.get("viability_id")) == str(native_cc.id):

                            pct = float(rule.get("percentage") or 0) / 100.0

                            break

                if pct == 1.0: # fallback

                    pct_raw = (native_cc.custom_data or {}).get("Participação Rateio")

                    try:

                        pct = float(str(pct_raw).replace('%','').replace(',','.')) / 100.0 if pct_raw else 1.0

                    except:

                        pct = 1.0

            else:

                pct = 1.0

                native_cc = type('obj', (object,), {'id': cc_id_int})() # dummy

                

            slice_act = _calc_slice_actuals(db, macro_prefix, native_cc.id, pct, view_mode, cached_cat_to_group)

            

            city, project_name = parse_project_name(main_cc)

            vendas_ativas = slice_act.get("vgv_vendido", 0.0) - slice_act.get("distratos", 0.0)

            vgv_total = vendas_ativas + slice_act.get("vgv_estoque", 0.0)

            perc_vendido = (vendas_ativas / vgv_total) * 100 if vgv_total > 0 else 0.0

            

            return {

                "db_id": db_id,

                "project_name": project_name,

                "category": "Em Andamento" if main_cc.project_phase != "Encerrado" else "Encerrado",

                "status": "Em comercialização" if main_cc.project_phase == "Em Andamento" else main_cc.project_phase,

                "city": city,

                "vgv_total": vgv_total,

                "vendas_acumuladas": vendas_ativas,

                "perc_vendido": perc_vendido,

                "lucro": slice_act.get("lucro_liq_operacional", 0.0),

                "tir_anual": slice_act.get("tir_anual", 0.0),

                "mtir_anual": slice_act.get("mtir_anual", 0.0),

                "payback_anos": slice_act.get("payback", 0),

                "exposicao_max_caixa": slice_act.get("exposicao_maxima") or 0.0,

                "exposicao_caixa_vgv": (abs(slice_act.get("exposicao_maxima") or 0.0) / vgv_total) * 100 if vgv_total > 0 else 0.0,

                "vso": 0.0,

                "distrato_venda": (slice_act.get("distratos", 0.0) / slice_act.get("vgv_vendido", 1.0)) * 100 if slice_act.get("vgv_vendido", 0.0) > 0 else 0.0,

                

                "actuals": slice_act,

                "dre": slice_act.get("dre", []),

                "fluxo_caixa": slice_act.get("fluxo_caixa", []),

                "planos_vendas": slice_act.get("planos_vendas", {}).get("distribuicao", []),

                "curto_longo": slice_act.get("planos_vendas", {}).get("curto_longo", []),

                "velocidade_vendas": slice_act.get("velocidade_vendas", [])

            }



        combined_final_cf = defaultdict(float)

        for sub_cc in ccs:

            # Partnership math

            custom = sub_cc.custom_data or {}

        

            p_config_id = custom.get("partnership_config_id")

            active_rules = {}

            if p_config_id:

                try:

                    p_config_id_int = int(p_config_id)

                    p_config = db.query(PartnershipConfig).filter(PartnershipConfig.id == p_config_id_int).first()

                    if p_config:

                        active_rules = p_config.rules

                except ValueError:

                    pass

            

            participacao_raw = custom.get("Participação", 0)

            try:

                if isinstance(participacao_raw, str):

                    participacao_raw = participacao_raw.replace('%', '').replace(',', '.')

                pct_parceiro = float(participacao_raw) / 100.0

            except:

                pct_parceiro = 0.0

            

            pct_empreendedor = 1.0 - pct_parceiro

        

            if view_mode == 'empreendedor':

                mult_default = 1.0

                mult_apportioned = pct_empreendedor

                _active_rules = active_rules

            elif view_mode == 'parceiro':

                mult_default = 0.0

                mult_apportioned = pct_parceiro

                _active_rules = active_rules

            else: # consolidado

                mult_default = 1.0

                mult_apportioned = 1.0

                _active_rules = None



            act = _calc_actuals_for_cc(db, sub_cc.id, active_rules=_active_rules, mult_apportioned=mult_apportioned, mult_default=mult_default, cached_cat_to_group=cached_cat_to_group)

        

            combined_actuals["vgv_vendido"] += act.get("vgv_vendido", 0.0)

            combined_actuals["vgv_estoque"] += act.get("vgv_estoque", 0.0)

            combined_actuals["estoque_unidades"] += act.get("estoque_unidades", 0) # integer

            combined_actuals["distratos"] += act.get("distratos", 0.0)

            combined_actuals["lucro_operacional"] += act.get("lucro_operacional", 0.0)

            combined_actuals["lucro_liq_operacional"] += act.get("lucro_liq_operacional", 0.0)

            combined_actuals["receita_bruta"] += act.get("receita_bruta", 0.0)

            combined_actuals["total_units"] += act.get("total_units", 0)

            combined_actuals["total_sold"] += act.get("total_sold", 0)

            combined_actuals["total_returned"] += act.get("total_returned", 0)

            combined_actuals["total_balance"] += act.get("total_balance", 0)

            

            for m, val in act.get("final_cf_dict", {}).items():

                combined_final_cf[m] += val

        

            # Sum DRE

            for row in act.get("dre", []):

                item_name = row["item"]

                if row.get("is_percentage", False) or isinstance(row["valor"], str):

                    continue

                if item_name not in combined_dre:

                    combined_dre[item_name] = {"item": item_name, "valor": 0.0, "bold": row.get("bold", False)}

                combined_dre[item_name]["valor"] += row["valor"]



            # Sum FC

            for row in act.get("fluxo_caixa", []):

                ano = row.get("Ano", row.get("ano"))

                if ano not in combined_fc:

                    combined_fc[ano] = {

                        "ano": ano, "Ano": ano, "Entradas": 0.0, "Devolucao_Distratos": 0.0, "Tributos": 0.0, "Terreno": 0.0,

                        "Obras": 0.0, "Projetos": 0.0, "Marketing": 0.0, "Comercial": 0.0,

                        "Administrativas": 0.0, "Saidas": 0.0, "Total_Saidas": 0.0, "Saldo_Mes": 0.0, "Saldo_Acumulado": 0.0,

                        "is_forecast": row.get("is_forecast", False)

                    }

                else:

                    if row.get("is_forecast"):

                        combined_fc[ano]["is_forecast"] = True



                for k in ["Entradas", "Devolucao_Distratos", "Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas"]:

                    combined_fc[ano][k] += row.get(k, 0.0)

                

                # Re-calculate saídas and saldo

                combined_fc[ano]["Saidas"] = sum([combined_fc[ano][k] for k in ["Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas"]])

                combined_fc[ano]["Total_Saidas"] = combined_fc[ano]["Saidas"] + combined_fc[ano]["Devolucao_Distratos"]

                combined_fc[ano]["Saldo_Mes"] = combined_fc[ano]["Entradas"] - combined_fc[ano]["Total_Saidas"]

        

            # Sum Velocidade de Vendas

            for vel_ano in act.get("velocidade_vendas", []):

                ano = vel_ano["ano"]

                combined_vel_anos[ano]["vendas"] += vel_ano["vendas"]

                combined_vel_anos[ano]["distratos"] += vel_ano["distratos"]

                for m_data in vel_ano.get("meses", []):

                    m = m_data["mes"]

                    combined_vel_anos[ano]["meses_dict"][m]["vendas"] += m_data["vendas"]

                    combined_vel_anos[ano]["meses_dict"][m]["distratos"] += m_data["distratos"]

                

            # Sum Planos de Vendas bins

            act_planos = act.get("planos_vendas")

            if act_planos and "distribuicao" in act_planos:

                # To reconstruct bins, we would need the raw values, but the act only has percentages.

                # Let's wait on planos_vendas and do it properly after the loop by querying the DB for all CCs, or we can just fetch all sales_transactions.

                pass



        indicators = _calculate_financial_indicators(combined_final_cf or {0: 0.0})

        combined_actuals["tir_anual"] = indicators.get("tir_anual") or 0.0

        combined_actuals["tir_mensal"] = indicators.get("tir_mensal") or 0.0

        combined_actuals["mtir_anual"] = indicators.get("mtir_anual") or 0.0

        combined_actuals["mtir_mensal"] = indicators.get("mtir_mensal") or 0.0

        combined_actuals["payback"] = indicators.get("payback") or 0

        combined_actuals["periodo_exposicao"] = indicators.get("periodo_exposicao") or 0

        combined_actuals["vida"] = indicators.get("vida") or 0

        combined_actuals["exposicao_maxima"] = indicators.get("exposicao_maxima") or 0.0



        # --- LÓGICA DE RATEIO HÍBRIDO (Slices) ---

        if is_slice:

                slice_cc = db.query(CostCenter).filter(CostCenter.id_sienge == cc_id).first()

                slice_pct = 1.0

                if slice_cc and slice_cc.apportionment_rules:

                    for rule in slice_cc.apportionment_rules:

                        if str(rule.get("project_prefix")) == str(slice_cc.id) or str(rule.get("project_prefix")) == str(getattr(slice_cc, "id_sienge", "")) or str(rule.get("viability_id")) == str(slice_cc.id):

                            slice_pct = float(rule.get("percentage") or 0) / 100.0

                            break

                        

                if slice_cc:

                    native_act = _calc_actuals_for_cc(db, slice_cc.id, cached_cat_to_group=cached_cat_to_group)

                else:

                    native_act = {}

            

                # Substituir KPIs Base

                combined_actuals["vgv_vendido"] = native_act.get("vgv_vendido", 0.0)

                combined_actuals["vgv_estoque"] = native_act.get("vgv_estoque", 0.0)

                combined_actuals["distratos"] = native_act.get("distratos", 0.0)

                combined_actuals["exposicao_maxima"] *= slice_pct

            

                # Ajustar DRE

                revenue_dre_keys = ["RECEITA BRUTA DE VENDAS", "DEDUÇÕES DA RECEITA BRUTA", "DISTRATOS"]

                native_dre = {}

                for row in native_act.get("dre", []):

                    if row.get("is_percentage", False) or isinstance(row["valor"], str): continue

                    native_dre[row["item"]] = row["valor"]

                

                for item_name, data in combined_dre.items():

                    if item_name in revenue_dre_keys:

                        data["valor"] = native_dre.get(item_name, 0.0)

                    elif item_name in ["RECEITA LÍQUIDA", "MARGEM BRUTA", "LUCRO LÍQUIDO OPERACIONAL"]:

                        pass # Recalculado

                    else:

                        data["valor"] *= slice_pct

                    

                # Recalcula totais do DRE

                rec_bruta = combined_dre.get("RECEITA BRUTA DE VENDAS", {}).get("valor", 0.0)

                deducoes = combined_dre.get("DEDUÇÕES DA RECEITA BRUTA", {}).get("valor", 0.0)

                distratos_dre = combined_dre.get("DISTRATOS", {}).get("valor", 0.0)

            

                rec_liq_val = rec_bruta + deducoes + distratos_dre

                if "RECEITA LÍQUIDA" in combined_dre: combined_dre["RECEITA LÍQUIDA"]["valor"] = rec_liq_val

            

                custos = combined_dre.get("CUSTOS INFR + CONST + TERR + PROJ", {}).get("valor", 0.0)

                margem_val = rec_liq_val + custos

                if "MARGEM BRUTA" in combined_dre: combined_dre["MARGEM BRUTA"]["valor"] = margem_val

            

                despesas = sum([v["valor"] for k,v in combined_dre.items() if k in ["CUSTOS COMERCIAIS", "DESPESAS ADMINISTRATIVAS", "OUTRAS DESPESAS / RECEITAS", "IMPOSTOS", "CUSTOS FINANCEIROS"]])

                lucro_val = margem_val + despesas

                if "LUCRO LÍQUIDO OPERACIONAL" in combined_dre: combined_dre["LUCRO LÍQUIDO OPERACIONAL"]["valor"] = lucro_val

                combined_actuals["lucro_operacional"] = lucro_val

            

                # Ajustar Fluxo de Caixa

                native_fc = {}

                for row in native_act.get("fluxo_caixa", []):

                    ano = row.get("Ano", row.get("ano"))

                    native_fc[ano] = {"Entradas": row.get("Entradas", 0.0), "Devolucao_Distratos": row.get("Devolucao_Distratos", 0.0)}

                

                for ano, fc_row in combined_fc.items():

                    fc_row["Entradas"] = native_fc.get(ano, {}).get("Entradas", 0.0)

                    fc_row["Devolucao_Distratos"] = native_fc.get(ano, {}).get("Devolucao_Distratos", 0.0)

                    for k in ["Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas"]:

                        fc_row[k] *= slice_pct

                    fc_row["Saidas"] = sum([fc_row[k] for k in ["Tributos", "Terreno", "Obras", "Projetos", "Marketing", "Comercial", "Administrativas"]])

                    fc_row["Total_Saidas"] = fc_row["Saidas"] + fc_row["Devolucao_Distratos"]

                    fc_row["Saldo_Mes"] = fc_row["Entradas"] - fc_row["Total_Saidas"]

        # ----------------------------------------

        

        # Sort and recalculate Saldo Acumulado for FC

        sorted_anos = sorted(combined_fc.keys())

        fc_list = []

        acum = 0.0

        for ano in sorted_anos:

                row = combined_fc[ano]

                acum += row["Saldo_Mes"]

                row["Saldo_Acumulado"] = acum

                fc_list.append(row)

            

        # Re-calculate percentages for DRE

        rec_liq = combined_dre.get("RECEITA LÍQUIDA", {}).get("valor", 0.0)

        marg_bru = combined_dre.get("MARGEM BRUTA", {}).get("valor", 0.0)

        luc_op = combined_dre.get("LUCRO LÍQUIDO OPERACIONAL", {}).get("valor", 0.0)

        

        mb_row = {

                "item": "Margem Bruta %",

                "valor": f"{(marg_bru / rec_liq * 100):.2f}%" if rec_liq > 0 else "0.00%",

                "is_percentage": True,

                "bold": True

        }

        

        mo_row = {

                "item": "Margem Operacional %",

                "valor": f"{(luc_op / rec_liq * 100):.2f}%" if rec_liq > 0 else "0.00%",

                "is_percentage": True,

                "bold": True

        }

            

        dre_list = []

        for v in combined_dre.values():

                dre_list.append(v)

                if v["item"] == "MARGEM BRUTA":

                    dre_list.append(mb_row)

                elif v["item"] == "LUCRO LÍQUIDO OPERACIONAL":

                    dre_list.append(mo_row)

        

        # Build Velocidade de Vendas for CG

        velocidade_vendas_list = []

        for ano in sorted(combined_vel_anos.keys()):

                v = combined_vel_anos[ano]["vendas"]

                d = combined_vel_anos[ano]["distratos"]

                saldo_ano = v - d

                vel_ano = (v / combined_actuals["total_units"]) * 100 if combined_actuals["total_units"] > 0 else 0

                perc_ano = (saldo_ano / combined_actuals["total_balance"]) * 100 if combined_actuals["total_balance"] > 0 else 0

            

                meses_list = []

                for m in sorted(combined_vel_anos[ano]["meses_dict"].keys()):

                    m_v = combined_vel_anos[ano]["meses_dict"][m]["vendas"]

                    m_d = combined_vel_anos[ano]["meses_dict"][m]["distratos"]

                    m_saldo = m_v - m_d

                    m_vel = (m_v / combined_actuals["total_units"]) * 100 if combined_actuals["total_units"] > 0 else 0

                    m_perc = (m_saldo / combined_actuals["total_balance"]) * 100 if combined_actuals["total_balance"] > 0 else 0

                    meses_list.append({

                        "mes": m,

                        "vendas": m_v,

                        "distratos": m_d,

                        "saldo": m_saldo,

                        "perc": round(m_perc, 2),

                        "vel": round(m_vel, 2)

                    })

                

                velocidade_vendas_list.append({

                    "ano": ano,

                    "vendas": v,

                    "distratos": d,

                    "saldo": saldo_ano,

                    "perc": round(perc_ano, 2),

                    "vel": round(vel_ano, 2),

                    "meses": meses_list

                })

            

        # Build Planos de Vendas for CG

        cc_ids = [c.id for c in ccs]

        sales_transactions = db.query(ActualTransaction).filter(

                ActualTransaction.cost_center_id.in_(cc_ids),

                ActualTransaction.transaction_type == "SALE",

                ActualTransaction.category.in_(["VGV Vendido", "Distrato"])

        ).all()

        

        for t in sales_transactions:

                inst = t.installments_number or 0

                val = abs(t.value)

                if inst <= 6: combined_planos_bins['Até 6X'] += val

                elif inst <= 12: combined_planos_bins['Até 12x'] += val

                elif inst <= 24: combined_planos_bins['Até 24x'] += val

                elif inst <= 36: combined_planos_bins['Até 36x'] += val

                elif inst <= 48: combined_planos_bins['Até 48x'] += val

                elif inst <= 60: combined_planos_bins['Até 60x'] += val

                elif inst <= 120: combined_planos_bins['Até 120x'] += val

                elif inst <= 156: combined_planos_bins['Até 156x'] += val

                else: combined_planos_bins['Até 180x'] += val

            

        total_planos = sum(combined_planos_bins.values())

        distribuicao = []

        val_curto = 0.0

        val_longo = 0.0

        for k, v in combined_planos_bins.items():

                perc = (v / total_planos * 100) if total_planos > 0 else 0

                if k in ['Até 6X', 'Até 12x', 'Até 24x', 'Até 36x', 'Até 48x']:

                    val_curto += v

                    distribuicao.append({"name": k, "curto": round(perc, 1), "longo": 0})

                else:

                    val_longo += v

                    distribuicao.append({"name": k, "curto": 0, "longo": round(perc, 1)})

                

        planos_vendas = {

                "curto_longo": [

                    {"name": "Plano Curto", "value": round((val_curto / total_planos * 100) if total_planos > 0 else 0, 1), "color": "#0F5B30"},

                    {"name": "Plano Longo", "value": round((val_longo / total_planos * 100) if total_planos > 0 else 0, 1), "color": "#94a3b8"}

                ],

                "distribuicao": distribuicao

        }



        

        # Inserimos a info de Estoque na DRE como informativo extra

        dre_list.append({"item": f"VGV Estoque Potencial ({combined_actuals['estoque_unidades']} unidades)", "valor": combined_actuals["vgv_estoque"], "bold": True})

        

        # Calculate rent_inv

        rent_inv = (combined_actuals["lucro_liq_operacional"] / combined_actuals["receita_bruta"]) * 100 if combined_actuals["receita_bruta"] > 0 else 0.0

        

        vendas_ativas_comb = combined_actuals["vgv_vendido"] - combined_actuals["distratos"]

        vgv_total_comb = vendas_ativas_comb + combined_actuals["vgv_estoque"]



        return {

                "kpis": {

                    "vgv_total": vgv_total_comb,
                    "vendas_acumuladas": vendas_ativas_comb,
                    "perc_vendido": (vendas_ativas_comb / vgv_total_comb * 100) if vgv_total_comb > 0 else 0.0,
                    "lucro": combined_actuals.get("lucro_liq_operacional", 0.0),
                    "vso": 0.0,
                    "distrato_venda": (combined_actuals.get("distratos", 0) / combined_actuals.get("vgv_vendido", 1)) * 100 if combined_actuals.get("vgv_vendido", 0) > 0 else 0.0,
                    "tir_anual": combined_actuals.get("tir_anual", 0.0),

                    "tir_mensal": combined_actuals.get("tir_mensal", 0.0),

                    "mtir_anual": combined_actuals.get("mtir_anual", 0.0),

                    "mtir_mensal": combined_actuals.get("mtir_mensal", 0.0),

                    "payback": combined_actuals.get("payback", 0),

                    "periodo_exposicao": combined_actuals.get("periodo_exposicao", 0),

                    "vida": combined_actuals.get("vida", 0),

                    "exposicao_max_caixa": combined_actuals.get("exposicao_maxima") or 0.0,

                    "exposicao_caixa_vgv": (abs(combined_actuals.get("exposicao_maxima") or 0.0) / vgv_total_comb) * 100 if vgv_total_comb > 0 else 0.0,

                    "rent_inv": rent_inv

                },

                "dre": dre_list,

                "fluxo_caixa": fc_list,

                "planos_vendas": planos_vendas,

                "velocidade_vendas": velocidade_vendas_list,

                "total_units": combined_actuals.get("total_units", 0),

                "total_sold": combined_actuals.get("total_sold", 0),

                "total_returned": combined_actuals.get("total_returned", 0),

                "total_balance": combined_actuals.get("total_balance", 0)

        }

        

    elif item_type == "c":

        # Retorna o Realizado para o Centro de Custo único (Fallback)

        c = db.query(CostCenter).filter(CostCenter.id == db_id).first()

        if not c:

                raise HTTPException(status_code=404, detail="Centro de Custo não encontrado.")

            

        actuals = _calc_actuals_for_cc(db, c.id)

        

        dre = actuals["dre"]

        dre.append({"item": f"VGV Estoque Potencial ({actuals['estoque_unidades']} unidades)", "valor": actuals["vgv_estoque"], "bold": True})

        

        return {

                "kpis": {

                    "vgv_total": actuals.get("vgv_vendido", 0.0) + actuals.get("vgv_estoque", 0.0),
                    "vendas_acumuladas": actuals.get("vgv_vendido", 0.0),
                    "perc_vendido": (actuals.get("vgv_vendido", 0.0) / (actuals.get("vgv_vendido", 0.0) + actuals.get("vgv_estoque", 0.0)) * 100) if (actuals.get("vgv_vendido", 0.0) + actuals.get("vgv_estoque", 0.0)) > 0 else 0.0,
                    "lucro": actuals.get("lucro_liq_operacional", 0.0),
                    "vso": 0.0,
                    "distrato_venda": (actuals.get("distratos", 0) / actuals.get("vgv_vendido", 1)) * 100 if actuals.get("vgv_vendido", 0) > 0 else 0.0,
                    "tir_anual": actuals.get("tir_anual", 0.0),

                    "tir_mensal": actuals.get("tir_mensal", 0.0),

                    "mtir_anual": actuals.get("mtir_anual", 0.0),

                    "mtir_mensal": actuals.get("mtir_mensal", 0.0),

                    "payback": actuals.get("payback", 0),

                    "periodo_exposicao": actuals.get("periodo_exposicao", 0),

                    "vida": actuals.get("vida", 0),

                    "exposicao_max_caixa": actuals.get("exposicao_maxima") or 0.0,

                    "exposicao_caixa_vgv": (abs(actuals.get("exposicao_maxima") or 0.0) / (actuals["vgv_vendido"] + actuals["vgv_estoque"])) * 100 if (actuals["vgv_vendido"] + actuals["vgv_estoque"]) > 0 else 0.0,

                    "rent_inv": actuals.get("rent_inv", 0.0)

                },

                "dre": dre,

                "fluxo_caixa": actuals["fluxo_caixa"],

                "planos_vendas": actuals.get("planos_vendas"),

                "velocidade_vendas": actuals.get("velocidade_vendas", []),

                "total_units": actuals.get("total_units", 0),

                "total_sold": actuals.get("total_sold", 0),

                "total_returned": actuals.get("total_returned", 0),

                "total_balance": actuals.get("total_balance", 0)

        }

        

    elif item_type == "v":

        # Retorna o Orçado da Viabilidade

        calc = {}

        cf_records = []

        v = db.query(Viability).filter(Viability.id == db_id).first()

        if v and v.phases:

                try:

                    res = calculate_viability_results(db, v.phases[0].id)

                    if "indicators" in res: calc = res["indicators"]

                    if "monthly_cashflow" in res: cf_records = res["monthly_cashflow"]

                except Exception:

                    pass



        anual_cf = defaultdict(lambda: {"Entradas": 0, "Tributos": 0, "Obras": 0, "Projetos": 0, "Marketing": 0, "Comercial": 0, "Administrativas": 0, "Saidas": 0})

        for row in cf_records:

                mes = row.get("Mes")

                if not mes: continue

                try:

                    ano = str(mes)[:4]

                    anual_cf[ano]["Entradas"] += row.get("Receitas", 0)

                    anual_cf[ano]["Tributos"] += row.get("Impostos", 0)

                    anual_cf[ano]["Obras"] += row.get("Obras", 0) + row.get("Terreno", 0)

                    anual_cf[ano]["Projetos"] += row.get("Projetos", 0)

                    anual_cf[ano]["Marketing"] += row.get("Marketing", 0)

                    anual_cf[ano]["Comercial"] += row.get("Comercial", 0)

                    anual_cf[ano]["Administrativas"] += row.get("Administrativas", 0) + row.get("Despesas", 0)

                    anual_cf[ano]["Saidas"] += row.get("Despesas", 0) + row.get("Obras", 0) + row.get("Terreno", 0) + row.get("Projetos", 0) + row.get("Impostos", 0) + row.get("Marketing", 0) + row.get("Comercial", 0) + row.get("Administrativas", 0)

                except Exception:

                    continue



        fluxo_caixa = []

        for ano in sorted(anual_cf.keys()):

                fluxo_caixa.append({

                    "Ano": ano,

                    "Entradas": anual_cf[ano]["Entradas"],

                    "Tributos": anual_cf[ano]["Tributos"],

                    "Obras": anual_cf[ano]["Obras"],

                    "Projetos": anual_cf[ano]["Projetos"],

                    "Marketing": anual_cf[ano]["Marketing"],

                    "Comercial": anual_cf[ano]["Comercial"],

                    "Administrativas": anual_cf[ano]["Administrativas"],

                    "Total_Saidas": anual_cf[ano]["Saidas"],

                })

            

        dre = [

                {"item": "Receita Bruta", "valor": calc.get("vgv_total", 0.0), "bold": True},

                {"item": "(-) Deduções (Distratos)", "valor": 0.0, "bold": False},

                {"item": "(-) Impostos s/ Venda", "valor": calc.get("impostos", 0.0), "bold": False},

                {"item": "Receita Líquida", "valor": calc.get("vgv_total", 0.0) - calc.get("impostos", 0.0), "bold": True},

                {"item": "(-) Custo de Terreno", "valor": calc.get("valor_terreno", 0.0), "bold": False},

                {"item": "(-) Custos de Obra", "valor": calc.get("custo_obras", 0.0), "bold": False},

                {"item": "Lucro Bruto", "valor": calc.get("vgv_total", 0) - calc.get("impostos", 0) - calc.get("valor_terreno", 0) - calc.get("custo_obras", 0), "bold": True},

                {"item": "(-) Despesas Comerciais e MKT", "valor": calc.get("comercial", 0) + calc.get("marketing", 0), "bold": False},

                {"item": "(-) Despesas Administrativas", "valor": calc.get("adm_despesas", 0) + calc.get("adm_obras", 0), "bold": False},

                {"item": "Resultado Operacional", "valor": calc.get("lucro_liquido", 0), "bold": True},

        ]



        lucro_liquido_calc = calc.get("lucro_liquido", 0)

        exposicao_max_caixa_calc = calc.get("exposicao_maxima") or 0.0

        rent_inv = (lucro_liquido_calc / calc.get("vgv_total", 1.0)) * 100 if calc.get("vgv_total", 0.0) > 0 else 0.0



        return {

                "kpis": {

                    "vgv_total": calc.get("vgv_total", 0.0),
                    "vendas_acumuladas": 0.0,
                    "perc_vendido": 0.0,
                    "lucro": calc.get("lucro_liquido", 0.0),
                    "vso": 0.0,
                    "distrato_venda": 0.0,
                    "tir_anual": calc.get("tir_aa", 0.0),

                    "mtir_anual": calc.get("mtir_aa", 0.0),

                    "payback": calc.get("payback", 0.0),

                    "exposicao_max_caixa": exposicao_max_caixa_calc,

                    "exposicao_caixa_vgv": (abs(exposicao_max_caixa_calc) / calc.get("vgv_total", 1.0)) * 100 if calc.get("vgv_total") else 0.0,

                    "rent_inv": rent_inv

                },

                "dre": dre,

                "fluxo_caixa": fluxo_caixa,

                "planos_vendas": {

                    "curto_longo": [

                        {"name": "Plano Curto", "value": 78, "color": "#0F5B30"},

                        {"name": "Plano Longo", "value": 22, "color": "#94a3b8"}

                    ],

                    "distribuicao": [

                        {"name": "Até 12x", "curto": 15, "longo": 0},

                        {"name": "Até 24x", "curto": 25, "longo": 0},

                        {"name": "Até 36x", "curto": 38, "longo": 0},

                        {"name": "Até 48x", "curto": 0, "longo": 10},

                        {"name": "Até 60x", "curto": 0, "longo": 5},

                        {"name": "Até 120x", "curto": 0, "longo": 5},

                        {"name": "Até 156x", "curto": 0, "longo": 2}

                    ]

                },

                "velocidade_vendas": []

        }

@router.get("/debug_143")

def debug_143(db: Session = Depends(get_db)):

    from app.models.cost_center import CostCenter

    ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like("143%")).all()

    

    from collections import defaultdict

    combined_final_cf = defaultdict(float)

    

    out = []

    total_vgv = 0

    total_lucro = 0

    

    for c in ccs:

        act = _calc_actuals_for_cc(db, c.id)

        vgv = act.get("vgv_vendido", 0)

        lucro = act.get("lucro_operacional", 0)

        total_vgv += vgv

        total_lucro += lucro

        

        cf_dict = act.get("final_cf_dict", {})

        for m, v in cf_dict.items():

            combined_final_cf[m] += v

            

        out.append({"id_sienge": c.id_sienge, "nome": c.nome, "vgv": vgv, "lucro": lucro})

        

    inds = _calculate_financial_indicators(combined_final_cf or {0: 0.0})

    

    # Check JUST 14305

    c_14305 = next((c for c in ccs if c.id_sienge == "14305"), None)

    if c_14305:

        act_14305 = _calc_actuals_for_cc(db, c_14305.id)

        inds_14305 = _calculate_financial_indicators(act_14305.get("final_cf_dict", {}))

    else:

        inds_14305 = {}



    return {

        "total_vgv": total_vgv,

        "total_lucro": total_lucro,

        "indicators": inds,

        "ccs": out,

        "inds_14305_only": inds_14305,

        "combined_cf": combined_final_cf

    }

