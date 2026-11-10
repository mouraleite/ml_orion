import pandas as pd
import numpy_financial as npf
from sqlalchemy.orm import Session
import json
from app.models.phase import Phase
from app.models.curves import StandardCurve, PhaseCurve
from app.models.system_settings import SystemSettings

def calcular_custos_funding(db: Session, funding, custo_obras_total: float, vgv_total: float):
    if not funding:
        return 0.0, 0.0, 0.0
        
    volume = 0.0
    if funding.modo_volume == "fixo":
        volume = funding.volume_fixo
    else:
        volume = custo_obras_total * (funding.percentual_obra_financiado / 100)
        
    if volume <= 0 or funding.tipo_funding == "Plano Empresarial (Banco)":
        return volume, 0.0, 0.0
        
    setting = db.query(SystemSettings).filter(SystemSettings.key == "funding_rates").first()
    rates = setting.value if setting and setting.value else {}
    
    # Defaults just in case
    cvm_rates = rates.get("CVM", {})
    anbima_rates = rates.get("ANBIMA", {})
    b3_rates = rates.get("B3", {})
    sec_rates = rates.get("Securitizadoras", {}).get(funding.securitizadora, {})
    
    # 1. CVM
    tx_cvm = cvm_rates.get("ICVM_476", 0.0003) if funding.icvm == "ICVM 476" else cvm_rates.get("ICVM_400", 0.0005)
    custo_cvm = max(volume * tx_cvm, cvm_rates.get("Mínimo", 809.16))
    
    # 2. ANBIMA
    tx_anb = anbima_rates.get("Taxa_Registro", 0.000044)
    custo_anb = volume * tx_anb
    if funding.icvm == "ICVM 476":
        custo_anb = max(min(custo_anb, anbima_rates.get("Max_476", 3136)), anbima_rates.get("Min_476", 1568))
    else:
        custo_anb = max(min(custo_anb, anbima_rates.get("Max_400", 109910)), anbima_rates.get("Min_400", 15700))
        
    # 3. B3 Registro (Escalonado)
    b3_reg_rate = 0.0
    for r in b3_rates.get("Registro", []):
        if volume <= r["max"]:
            b3_reg_rate = r["rate"]
            break
    custo_b3_registro = volume * b3_reg_rate
    
    # 4. Securitizadora Upfront (Implantação, Custodiante, Registro Lastro)
    custo_sec_upfront = sec_rates.get("Agente_Fiduciario_Implantacao", 0) + sec_rates.get("Instituicao_Custodiante", 0) + sec_rates.get("Registro_Lastro", 0)
    
    custo_estruturacao = custo_cvm + custo_anb + custo_b3_registro + custo_sec_upfront
    if funding.taxa_estruturacao > 0:
        custo_estruturacao += volume * (funding.taxa_estruturacao / 100)
        
    # 5. Custos Recorrentes
    # B3 Custódia (Escalonado)
    b3_cust_rate = 0.0
    for r in b3_rates.get("Custodia", []):
        if volume <= r["max"]:
            b3_cust_rate = r["rate"]
            break
    custo_b3_custodia = volume * b3_cust_rate
    custo_sec_recorrente = sec_rates.get("Agente_Fiduciario_Recorrente", 0) + sec_rates.get("Liquidante", 0)
    
    custo_recorrente_anual = custo_b3_custodia + custo_sec_recorrente
    
    # Add Gross up
    gross_up = funding.gross_up / 100.0 if funding.gross_up else 0.0
    custo_estruturacao = custo_estruturacao / (1 - gross_up) if gross_up < 1 else custo_estruturacao
    custo_recorrente_anual = custo_recorrente_anual / (1 - gross_up) if gross_up < 1 else custo_recorrente_anual
    
    custo_recorrente_total = (custo_recorrente_anual / 12) * funding.prazo_meses
    
    return volume, custo_estruturacao, custo_recorrente_total

TIPOS_FUNDING_COM_CRONOGRAMA = ("Plano Empresarial (Banco)", "CRI", "CRA")


def taxa_mensal_funding(funding) -> float:
    """Taxa de juros do funding em decimal ao mês.
    taxa_juros_periodicidade: "a.a." (padrão) converte por (1+i)^(1/12) - 1; "a.m." usa direto."""
    taxa = (getattr(funding, "taxa_juros", 0.0) or 0.0) / 100.0
    periodicidade = (getattr(funding, "taxa_juros_periodicidade", None) or "a.a.").strip().lower()
    if taxa <= 0:
        return 0.0
    if periodicidade in ("a.m.", "am", "mensal"):
        return taxa
    return (1 + taxa) ** (1 / 12) - 1


def cronograma_funding(volume: float, taxa_mensal: float, prazo: int, sistema: str) -> list[tuple[float, float]]:
    """Lista de (juros, amortização) por mês de pagamento, do 1º ao último.
    A soma das amortizações é sempre o volume captado."""
    if volume <= 0 or prazo <= 0:
        return []
    sistema = sistema or "SAC"
    linhas = []
    if sistema == "Bullet":
        for j in range(prazo):
            juros = volume * taxa_mensal
            linhas.append((juros, volume if j == prazo - 1 else 0.0))
        return linhas
    if taxa_mensal <= 0:
        return [(0.0, volume / prazo) for _ in range(prazo)]
    saldo = volume
    if sistema == "Price":
        pmt = volume * (taxa_mensal / (1 - (1 + taxa_mensal) ** -prazo))
        for j in range(prazo):
            juros = saldo * taxa_mensal
            amort = saldo if j == prazo - 1 else pmt - juros
            linhas.append((juros, amort))
            saldo -= amort
        return linhas
    amort = volume / prazo  # SAC
    for j in range(prazo):
        juros = saldo * taxa_mensal
        linhas.append((juros, amort))
        saldo -= amort
    return linhas


def _extract_curve(json_field) -> tuple[list, int]:
    """
    Busca a curva vinculada à fase a partir do próprio JSON da linha.
    Retorna (valores_percentuais[], mes_inicio).
    """
    if not json_field or not isinstance(json_field, dict):
        return ([], 1)
    
    meses = json_field.get("meses", [])
    mes_inicio = json_field.get("mes_inicio", 1)
    
    total = sum(meses)
    if total > 0 and abs(total - 100.0) > 0.001:
        meses = [m * 100.0 / total for m in meses]
        
    return (meses, mes_inicio)


def _acelerar_curva(meses: list, fator: float) -> list:
    """Cenário de velocidade de vendas: fator 2 vende o mesmo total na metade do tempo;
    0,5 leva o dobro. Redistribui o acumulado da curva no novo prazo; a soma não muda."""
    if not meses or not fator or fator <= 0 or abs(fator - 1.0) < 1e-9:
        return list(meses)
    n = len(meses)
    acum = [0.0]
    for v in meses:
        acum.append(acum[-1] + v)

    def acumulado_ate(t: float) -> float:
        if t >= n:
            return acum[n]
        i = int(t)
        return acum[i] + (t - i) * meses[i]

    novo_n = max(1, int(round(n / fator)))
    return [acumulado_ate(min(n, (k + 1) * fator)) - acumulado_ate(min(n, k * fator)) for k in range(novo_n)]


def _apply_offset(distribution: list, mes_inicio: int, prazo: int) -> list:
    """
    Aplica o offset do mês de início na distribuição.
    Se mes_inicio=6, os percentuais começam no mês 6 (índice 5).
    Retorna um vetor de tamanho `prazo` com zeros nos meses antes do offset.
    """
    offset = max(0, mes_inicio - 1)
    result = [0.0] * prazo
    for i, val in enumerate(distribution):
        target_idx = offset + i
        if target_idx < prazo:
            result[target_idx] = val
    return result


from app.models.scenario import Scenario

def calculate_viability_results(db: Session, phase_id: int, scenario_id: int = None):
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        return {"error": "Phase not found"}

    # Extrair Cenário se fornecido
    vgv_mult = 1.0
    cost_mult = 1.0
    speed_mult = 1.0
    if scenario_id:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario:
            vgv_mult = scenario.vgv_multiplier or 1.0
            cost_mult = scenario.construction_cost_multiplier or 1.0
            speed_mult = scenario.sales_speed_multiplier or 1.0

    # Extrair premissas básicas
    vgv_total_base = phase.revenue.vgv_total if phase.revenue and phase.revenue.vgv_total else 0.0
    vgv_total = vgv_total_base * vgv_mult
    
    # Obras e CAPEX
    if phase.construction:
        val_obras = phase.construction.custo_obras or 0.0
        custo_obras = val_obras if getattr(phase.construction, 'custo_obras_tipo', 'R$') == 'R$' else vgv_total * (val_obras / 100)
        custo_obras *= cost_mult
        
        val_proj = phase.construction.custo_projetos or 0.0
        custo_projetos = val_proj if getattr(phase.construction, 'custo_projetos_tipo', 'R$') == 'R$' else vgv_total * (val_proj / 100)
        custo_projetos *= cost_mult
        
        val_aq = phase.construction.aquisicao_area or 0.0
        aquisicao_area = val_aq if getattr(phase.construction, 'aquisicao_area_tipo', 'R$') == 'R$' else vgv_total * (val_aq / 100)
        aquisicao_area *= cost_mult
        
        val_adm_obr = phase.construction.adm_obras or 0.0
        adm_obras = val_adm_obr if getattr(phase.construction, 'adm_obras_tipo', 'R$') == 'R$' else vgv_total * (val_adm_obr / 100)
        adm_obras *= cost_mult
        
        custo_obras_total = custo_obras + custo_projetos + aquisicao_area + adm_obras
    else:
        custo_obras = 0.0
        custo_projetos = 0.0
        aquisicao_area = 0.0
        adm_obras = 0.0
        custo_obras_total = 0.0
    
    # Despesas OPEX
    if phase.expenses:
        val_mkt = phase.expenses.marketing_valor or 0.0
        marketing = val_mkt if getattr(phase.expenses, 'marketing_tipo', '%') == 'R$' else vgv_total * (val_mkt / 100)
        
        val_comercial = phase.expenses.comercial_valor or 0.0
        comercial = val_comercial if getattr(phase.expenses, 'comercial_tipo', '%') == 'R$' else vgv_total * (val_comercial / 100)
        
        val_adm = phase.expenses.adm_valor or 0.0
        adm = val_adm if getattr(phase.expenses, 'adm_tipo', '%') == 'R$' else vgv_total * (val_adm / 100)
        
        val_comissao = getattr(phase.expenses, 'comissao_corretagem_valor', 0.0) or 0.0
        comissao = vgv_total * (val_comissao / 100)
    else:
        marketing = 0.0
        comercial = 0.0
        adm = 0.0
        comissao = 0.0

    # Reduz o VGV Total (Bruto) pela comissão (que é paga por fora)
    # Daqui para baixo, 'vgv_total' passa a atuar como VGV Líquido
    vgv_bruto = vgv_total
    vgv_total = vgv_bruto - comissao

    # Permutas e Rateios
    valor_terreno = 0.0
    mod_str = phase.exchanges.modalidade if phase.exchanges and phase.exchanges.modalidade else ""
    
    if "Dinheiro" in mod_str:
        valor_terreno += phase.exchanges.valor_terreno_fixo if phase.exchanges.valor_terreno_fixo else 0.0

    if "Permuta Financeira" in mod_str:
        rateios = phase.exchanges.rateios_config_json if phase.exchanges and getattr(phase.exchanges, 'rateios_config_json', None) else {}
        
        if rateios.get("vincular_permuta_parceria", True):
            perc_perm = phase.exchanges.perc_parceria_terrenista if phase.exchanges and getattr(phase.exchanges, 'perc_parceria_terrenista', None) else 0.0
        else:
            perc_perm = phase.exchanges.perc_permuta_financeira if phase.exchanges.perc_permuta_financeira else 0.0
            
        valor_terreno += vgv_total * (perc_perm / 100)
        
    if "Permuta Física" in mod_str:
        unidades = phase.exchanges.permuta_fisica_unidades if phase.exchanges and getattr(phase.exchanges, 'permuta_fisica_unidades', None) else 0
        valor_unidade = phase.exchanges.permuta_fisica_valor_unidade if phase.exchanges and getattr(phase.exchanges, 'permuta_fisica_valor_unidade', None) else 0.0
        valor_terreno += unidades * valor_unidade

    # Rateios de Verbas (Parcerias)
    rateios = phase.exchanges.rateios_config_json if phase.exchanges and getattr(phase.exchanges, 'rateios_config_json', None) else {}
    perc_terr = phase.exchanges.perc_parceria_terrenista if phase.exchanges and getattr(phase.exchanges, 'perc_parceria_terrenista', None) else 0.0
    fator_empreendedor = 1.0 - (perc_terr / 100.0)

    # Abatimento de Custos (O que tiver rateio=True, multiplica pelo fator do Empreendedor)
    # COMENTADO: A DRE Global deve refletir 100% dos custos. A redução por ótica (Empreendedor/Parceiro) 
    # deve ser tratada no frontend através do multiplicador de viewMode.
    # if rateios.get("custo_obras", False):
    #     custo_obras *= fator_empreendedor
    # if rateios.get("custo_projetos", False):
    #     custo_projetos *= fator_empreendedor
    # if rateios.get("aquisicao_area", False):
    #     aquisicao_area *= fator_empreendedor
    # if rateios.get("adm_obras", False):
    #     adm_obras *= fator_empreendedor
    
    custo_obras_total = custo_obras + custo_projetos + aquisicao_area + adm_obras

    # if rateios.get("marketing", False):
    #     marketing *= fator_empreendedor
    # if rateios.get("comercial", False):
    #     comercial *= fator_empreendedor
    #     comissao *= fator_empreendedor
    # if rateios.get("adm", False):
    #     adm *= fator_empreendedor
    extra_constructions = []
    if phase.construction and getattr(phase.construction, 'extra_constructions_json', None):
        for ec in phase.construction.extra_constructions_json:
            val = ec.get('valor', 0.0)
            tipo = ec.get('tipo', 'R$')
            final_val = val if tipo == 'R$' else vgv_total * (val / 100)
            # Extra Rateio
            # key no json: extra_obra_0, extra_obra_1, etc.
            # idx = len(extra_constructions)
            # if rateios.get(f"extra_obra_{idx}", False):
            #     final_val *= fator_empreendedor
                
            final_val *= cost_mult
            custo_obras_total += final_val
            extra_constructions.append({
                "valor": final_val,
                "curva_json": ec.get('curva_json', None)
            })

    # A comissão foi deduzida da receita e não entra na DRE como despesa
    total_despesas = marketing + comercial + adm
    
    # Despesas OPEX Extras
    extra_expenses = []
    if phase.expenses and getattr(phase.expenses, 'extra_expenses_json', None):
        for ee in phase.expenses.extra_expenses_json:
            val = ee.get('valor', 0.0)
            tipo = ee.get('tipo', 'R$')
            final_val = val if tipo == 'R$' else vgv_total * (val / 100)
            # Extra Rateio
            # idx = len(extra_expenses)
            # if rateios.get(f"extra_despesa_{idx}", False):
            #     final_val *= fator_empreendedor
                
            total_despesas += final_val
            extra_expenses.append({
                "valor": final_val,
                "curva_json": ee.get('curva_json', None)
            })
    # Impostos
    regime = phase.taxes.regime_tributario if phase.taxes and phase.taxes.regime_tributario else "RET"
    incidencia_sobre = getattr(phase.taxes, 'incidencia_sobre', "Recebimento") if phase.taxes else "Recebimento"
    
    prop_pis = 0.0
    prop_cofins = 0.0
    prop_irpj_csll = 0.0
    prop_outros = 0.0

    if regime == "Lucro Presumido":
        a_pis = phase.taxes.aliquota_pis or 0.65
        a_cofins = phase.taxes.aliquota_cofins or 3.0
        a_irpj = phase.taxes.aliquota_irpj or 1.20
        a_csll = phase.taxes.aliquota_csll or 1.08
        a_outros = phase.taxes.aliquota_outros or 0.0
        aliquota_imposto = a_pis + a_cofins + a_irpj + a_csll + a_outros
        if aliquota_imposto > 0:
            prop_pis = a_pis / aliquota_imposto
            prop_cofins = a_cofins / aliquota_imposto
            prop_irpj_csll = (a_irpj + a_csll) / aliquota_imposto
            prop_outros = a_outros / aliquota_imposto
    else:
        aliquota_imposto = phase.taxes.aliquota_total if phase.taxes and getattr(phase.taxes, 'aliquota_total', None) is not None else 4.0
        # RET: proporções fixas relativas à alíquota RET padrão de 4%
        # PIS=0.37%, COFINS=1.71%, IRPJ+CSLL=1.92% (total=4%)
        # Mas se aliquota_total foi customizada, mantemos proporções relativas
        _ret_base = 4.0
        prop_pis = 0.37 / _ret_base
        prop_cofins = 1.71 / _ret_base
        prop_irpj_csll = 1.92 / _ret_base
        prop_outros = max(0.0, (aliquota_imposto - _ret_base) / aliquota_imposto) if aliquota_imposto > _ret_base else 0.0
        # Renormaliza para que props somem 1.0
        _prop_sum = prop_pis + prop_cofins + prop_irpj_csll + prop_outros
        if _prop_sum > 0 and abs(_prop_sum - 1.0) > 0.001:
            prop_pis /= _prop_sum
            prop_cofins /= _prop_sum
            prop_irpj_csll /= _prop_sum
            prop_outros /= _prop_sum

    total_impostos = vgv_total * (aliquota_imposto / 100)

    # ---- Juros e Amortizacao das Vendas ----
    import re
    def _parse_condicoes(condicoes_json):
        if not isinstance(condicoes_json, list) or len(condicoes_json) == 0:
            return [{"nome": "A VISTA", "perc": 100.0, "inst": 1, "aplica_juros": True, "aplica_correcao": True}]
        
        # Se for uma lista de planos (ex: [{"nome": "Plano 1", "condicoes": [...]}]), extrai as condicoes
        flat_conds = []
        for item in condicoes_json:
            if "condicoes" in item and isinstance(item["condicoes"], list):
                flat_conds.extend(item["condicoes"])
            else:
                flat_conds.append(item)
                
        if not flat_conds:
            return [{"nome": "A VISTA", "perc": 100.0, "inst": 1, "aplica_juros": True, "aplica_correcao": True}]

        parsed = []
        for cond in flat_conds:
            nome = str(cond.get("nome", "1")).upper().replace("A VISTA", "1")
            perc = cond.get("perc", 0.0)
            aplica_juros = cond.get("aplica_juros", True)
            aplica_correcao = cond.get("aplica_correcao", True)
            m = re.search(r'\d+', nome)
            inst = int(m.group()) if m else 1
            if inst <= 0: inst = 1
            perc_entrada = cond.get("perc_entrada", 0.0)
            parcelas_entrada = cond.get("parcelas_entrada", 1)
            curve_json = cond.get("curve_json", None)
            parsed.append({"nome": nome, "perc": perc, "inst": inst, "aplica_juros": aplica_juros, "aplica_correcao": aplica_correcao, "perc_entrada": perc_entrada, "parcelas_entrada": parcelas_entrada, "curve_json": curve_json})
        return parsed

    condicoes = _parse_condicoes(phase.revenue.condicoes_pagamento_json if phase.revenue else [])
    max_inst = max([c["inst"] for c in condicoes]) if condicoes else 1
    
    sistema_amortizacao = phase.revenue.sistema_amortizacao if phase.revenue and getattr(phase.revenue, "sistema_amortizacao", None) else "Sem Juros"
    taxa_juros = float(phase.revenue.taxa_juros_vendas) if phase.revenue and getattr(phase.revenue, "taxa_juros_vendas", None) else 0.0
    # Converte a taxa anual para mensal (juros compostos)
    taxa_juros_decimal = (1 + (taxa_juros / 100.0)) ** (1/12) - 1
    
    taxa_inf = float(phase.revenue.taxa_correcao_projetada) if phase.revenue and getattr(phase.revenue, "taxa_correcao_projetada", None) else 0.0
    tipo_inf = phase.revenue.tipo_correcao_projetada if phase.revenue and getattr(phase.revenue, "tipo_correcao_projetada", None) else "% a.a."
    taxa_inf_mensal = taxa_inf / 100.0
    if tipo_inf == "% a.a.":
        taxa_inf_mensal = ((1 + taxa_inf_mensal) ** (1/12.0)) - 1
        
    taxa_incc_mensal = 0.0
    if phase.viability and getattr(phase.viability, 'aplicar_incc_obras', False):
        taxa_incc = getattr(phase.viability, 'incc_projetado_valor', 0.0) or 0.0
        tipo_incc = getattr(phase.viability, 'incc_projetado_tipo', '% a.a.') or '% a.a.'
        taxa_incc_dec = taxa_incc / 100.0
        if tipo_incc == "% a.a.":
            taxa_incc_mensal = ((1 + taxa_incc_dec) ** (1/12.0)) - 1
        else:
            taxa_incc_mensal = taxa_incc_dec

    # ---- Distribuição por Curvas Dinâmicas ----
    def _curva_vendas(json_field):
        raw, offset = _extract_curve(json_field)
        return _acelerar_curva(raw, speed_mult), offset

    vendas_raw, vendas_offset = _curva_vendas(phase.revenue.velocidade_vendas_json if phase.revenue else None)
    obras_raw, obras_offset = _extract_curve(phase.construction.curva_obras_json if phase.construction else None)
    projetos_raw, proj_offset = _extract_curve(phase.construction.curva_projetos_json if phase.construction else None)
    aquisicao_raw, aq_offset = _extract_curve(phase.construction.curva_aquisicao_json if phase.construction else None)
    adm_obras_raw, adm_obr_offset = _extract_curve(phase.construction.curva_adm_obras_json if phase.construction else None)
    
    marketing_raw, mkt_offset = _extract_curve(phase.expenses.curva_marketing_json if phase.expenses else None)
    comercial_raw, com_offset = _extract_curve(phase.expenses.curva_comercial_json if phase.expenses else None)
    adm_desp_raw, adm_desp_offset = _extract_curve(phase.expenses.curva_adm_json if phase.expenses else None)

    extra_mkt_dists = []
    for ee in extra_expenses:
        raw, offset = _extract_curve(ee.get("curva_json"))
        extra_mkt_dists.append({"raw": raw, "offset": offset, "valor": ee["valor"]})
        
    extra_obr_dists = []
    for ec in extra_constructions:
        raw, offset = _extract_curve(ec.get("curva_json"))
        extra_obr_dists.append({"raw": raw, "offset": offset, "valor": ec["valor"]})

    # Determinar o prazo baseado no maior vetor (com offset)
    max_length = 36  # mínimo padrão
    
    # Considera a curva global de vendas e as específicas de cada condição
    for cond in condicoes:
        if cond.get("curve_json"):
            c_raw, c_offset = _curva_vendas(cond.get("curve_json"))
            c_offset = vendas_offset + max(0, c_offset - 1)
        else:
            c_raw, c_offset = vendas_raw, vendas_offset
            
        total_len = len(c_raw) + max(0, c_offset - 1)
        if total_len > max_length:
            max_length = total_len
            
    for dist, offset in [(obras_raw, obras_offset), (marketing_raw, mkt_offset)]:
        total_len = len(dist) + max(0, offset - 1)
        if total_len > max_length:
            max_length = total_len
            
    for d in extra_mkt_dists + extra_obr_dists:
        total_len = len(d["raw"]) + max(0, d["offset"] - 1)
        if total_len > max_length:
            max_length = total_len
    
    prazo = max(max_length + 1, max_length + max_inst)  # +1 para o mês de CRI/Funding, expandido pelas parcelas

    # Aplicar offsets
    vendas_dist = _apply_offset(vendas_raw, vendas_offset, prazo)
    obras_dist = _apply_offset(obras_raw, obras_offset, prazo)
    proj_dist = _apply_offset(projetos_raw, proj_offset, prazo)
    aq_dist = _apply_offset(aquisicao_raw, aq_offset, prazo)
    adm_obr_dist = _apply_offset(adm_obras_raw, adm_obr_offset, prazo)
    
    mkt_dist = _apply_offset(marketing_raw, mkt_offset, prazo)
    com_dist = _apply_offset(comercial_raw, com_offset, prazo)
    adm_desp_dist = _apply_offset(adm_desp_raw, adm_desp_offset, prazo)
    
    for d in extra_mkt_dists:
        d["dist"] = _apply_offset(d["raw"], d["offset"], prazo)
    for d in extra_obr_dists:
        d["dist"] = _apply_offset(d["raw"], d["offset"], prazo)

    # Criação do Vetor
    df = pd.DataFrame({"Mes": range(1, prazo + 1)})
    
    rec_vetor = [0.0] * prazo
    rec_vendas_vetor = [0.0] * prazo
    rec_entrada_vetor = [0.0] * prazo
    rec_parcelas_vetor = [0.0] * prazo
    rec_juros_vetor = [0.0] * prazo
    obr_vetor = []
    obr_custo_vetor = []
    obr_proj_vetor = []
    obr_aq_vetor = []
    obr_adm_vetor = []
    obr_extra_vetors = [[] for _ in extra_obr_dists]
    
    desp_vetor = []
    desp_mkt_vetor = []
    desp_com_vetor = []
    desp_adm_vetor = []
    desp_extra_vetors = [[] for _ in extra_mkt_dists]
    imp_vetor = [0.0] * prazo
    imp_pis_vetor = [0.0] * prazo
    imp_cofins_vetor = [0.0] * prazo
    imp_irpj_csll_vetor = [0.0] * prazo
    imp_outros_vetor = [0.0] * prazo
    
    # ---- Aplicação do Plano de Pagamentos (Recebimentos) ----
    for cond in condicoes:
        if cond["perc"] <= 0: continue
        
        if cond.get("curve_json"):
            c_raw, c_offset = _curva_vendas(cond.get("curve_json"))
            c_offset = vendas_offset + max(0, c_offset - 1)
        else:
            c_raw, c_offset = vendas_raw, vendas_offset
            
        cond_dist = _apply_offset(c_raw, c_offset, prazo)
        
        # Fallback de curva de vendas para a condição: se nenhuma curva configurada, distribui uniformemente.
        if sum(cond_dist) == 0 and vgv_total > 0:
            n_meses_venda = max(36, prazo - max_inst)
            perc_por_mes = 100.0 / n_meses_venda
            for i in range(min(n_meses_venda, prazo)):
                cond_dist[i] = perc_por_mes

        val_total_plano = vgv_total * (cond["perc"] / 100.0)
        imp_total_plano = total_impostos * (cond["perc"] / 100.0)

        for i in range(len(cond_dist)):
            if cond_dist[i] > 0:
                val_total_condicao = val_total_plano * (cond_dist[i] / 100.0)
                imp_total_condicao = imp_total_plano * (cond_dist[i] / 100.0)

                if incidencia_sobre == "Venda" and i < prazo:
                    imp_vetor[i] += imp_total_condicao
                    imp_pis_vetor[i] += imp_total_condicao * prop_pis
                    imp_cofins_vetor[i] += imp_total_condicao * prop_cofins
                    imp_irpj_csll_vetor[i] += imp_total_condicao * prop_irpj_csll
                    imp_outros_vetor[i] += imp_total_condicao * prop_outros

                perc_entrada = cond.get("perc_entrada", 0.0)
                parcelas_entrada = max(1, cond.get("parcelas_entrada", 1))

                val_entrada_total = val_total_condicao * (perc_entrada / 100.0)
                imp_entrada_total = imp_total_condicao * (perc_entrada / 100.0)

                val_financiado = val_total_condicao - val_entrada_total
                imp_financiado = imp_total_condicao - imp_entrada_total
                
                # Aplica as parcelas da entrada imediatamente (sem juros e sem inflação)
                if val_entrada_total > 0:
                    val_entrada_mensal = val_entrada_total / parcelas_entrada
                    imp_entrada_mensal = imp_entrada_total / parcelas_entrada
                    
                    for p in range(parcelas_entrada):
                        idx_entrada = i + p
                        if idx_entrada < prazo:
                            rec_vetor[idx_entrada] += val_entrada_mensal
                            rec_vendas_vetor[idx_entrada] += val_entrada_mensal
                            rec_entrada_vetor[idx_entrada] += val_entrada_mensal
                            if incidencia_sobre != "Venda":
                                imp_vetor[idx_entrada] += imp_entrada_mensal
                                imp_pis_vetor[idx_entrada] += imp_entrada_mensal * prop_pis
                                imp_cofins_vetor[idx_entrada] += imp_entrada_mensal * prop_cofins
                                imp_irpj_csll_vetor[idx_entrada] += imp_entrada_mensal * prop_irpj_csll
                                imp_outros_vetor[idx_entrada] += imp_entrada_mensal * prop_outros

                inst = cond["inst"]
                if val_entrada_total > 0 and inst > parcelas_entrada:
                    inst = inst - parcelas_entrada
                
                if inst <= 0:
                    continue  # Se inst=0, todo o valor deveria ter sido pago na entrada
                
                # Offset para início das parcelas financiadas
                if inst == 1 and val_entrada_total == 0:
                    offset_financiamento = 0
                else:
                    offset_financiamento = parcelas_entrada if val_entrada_total > 0 else 1
                
                cond_taxa_juros = taxa_juros_decimal if cond.get("aplica_juros", True) else 0.0
                cond_taxa_inf = taxa_inf_mensal if cond.get("aplica_correcao", True) else 0.0
                
                if sistema_amortizacao == "Price" and cond_taxa_juros > 0:
                    parcela_mensal = val_financiado * (cond_taxa_juros / (1 - (1 + cond_taxa_juros) ** -inst))
                    imp_parcela = imp_financiado * (cond_taxa_juros / (1 - (1 + cond_taxa_juros) ** -inst))
                    saldo_devedor = val_financiado
                    imp_saldo_devedor = imp_financiado
                    for j in range(inst):
                        idx_fin = i + offset_financiamento + j
                        if idx_fin < prazo:
                            juros_mes = saldo_devedor * cond_taxa_juros
                            amort_mes = parcela_mensal - juros_mes
                            saldo_devedor -= amort_mes
                            
                            imp_juros_mes = imp_saldo_devedor * cond_taxa_juros
                            imp_amort_mes = imp_parcela - imp_juros_mes
                            imp_saldo_devedor -= imp_amort_mes
                            
                            fator_inf = (1 + cond_taxa_inf) ** (offset_financiamento + j)
                            
                            parcela_total = parcela_mensal * fator_inf
                            rec_vendas = amort_mes
                            rec_juros = parcela_total - amort_mes
                            
                            rec_vetor[idx_fin] += parcela_total
                            rec_vendas_vetor[idx_fin] += rec_vendas
                            rec_parcelas_vetor[idx_fin] += rec_vendas
                            rec_juros_vetor[idx_fin] += rec_juros
                            
                            if incidencia_sobre != "Venda":
                                imp_atual = imp_parcela * fator_inf
                                imp_vetor[idx_fin] += imp_atual
                                imp_pis_vetor[idx_fin] += imp_atual * prop_pis
                                imp_cofins_vetor[idx_fin] += imp_atual * prop_cofins
                                imp_irpj_csll_vetor[idx_fin] += imp_atual * prop_irpj_csll
                                imp_outros_vetor[idx_fin] += imp_atual * prop_outros
                
                elif sistema_amortizacao == "SAC" and cond_taxa_juros > 0:
                    amort_mensal = val_financiado / inst
                    imp_amort_mensal = imp_financiado / inst
                    for j in range(inst):
                        idx_fin = i + offset_financiamento + j
                        if idx_fin < prazo:
                            saldo_devedor = val_financiado - (amort_mensal * j)
                            imp_saldo_devedor = imp_financiado - (imp_amort_mensal * j)
                            juros_mes = saldo_devedor * cond_taxa_juros
                            imp_juros_mes = imp_saldo_devedor * cond_taxa_juros
                            
                            fator_inf = (1 + cond_taxa_inf) ** (offset_financiamento + j)
                            
                            parcela_total = (amort_mensal + juros_mes) * fator_inf
                            rec_vendas = amort_mensal
                            rec_juros = parcela_total - amort_mensal
                            
                            rec_vetor[idx_fin] += parcela_total
                            rec_vendas_vetor[idx_fin] += rec_vendas
                            rec_parcelas_vetor[idx_fin] += rec_vendas
                            rec_juros_vetor[idx_fin] += rec_juros
                            
                            if incidencia_sobre != "Venda":
                                imp_atual = (imp_amort_mensal + imp_juros_mes) * fator_inf
                                imp_vetor[idx_fin] += imp_atual
                                imp_pis_vetor[idx_fin] += imp_atual * prop_pis
                                imp_cofins_vetor[idx_fin] += imp_atual * prop_cofins
                                imp_irpj_csll_vetor[idx_fin] += imp_atual * prop_irpj_csll
                                imp_outros_vetor[idx_fin] += imp_atual * prop_outros
                else:
                    parcela_mensal = val_financiado / inst
                    imp_parcela = imp_financiado / inst
                    for j in range(inst):
                        idx_fin = i + offset_financiamento + j
                        if idx_fin < prazo:
                            fator_inf = (1 + cond_taxa_inf) ** (offset_financiamento + j)
                            
                            parcela_total = parcela_mensal * fator_inf
                            rec_vendas = parcela_mensal
                            rec_juros = parcela_total - parcela_mensal
                            
                            rec_vetor[idx_fin] += parcela_total
                            rec_vendas_vetor[idx_fin] += rec_vendas
                            rec_parcelas_vetor[idx_fin] += rec_vendas
                            rec_juros_vetor[idx_fin] += rec_juros
                            
                            if incidencia_sobre != "Venda":
                                imp_atual = imp_parcela * fator_inf
                                imp_vetor[idx_fin] += imp_atual
                                imp_pis_vetor[idx_fin] += imp_atual * prop_pis
                                imp_cofins_vetor[idx_fin] += imp_atual * prop_cofins
                                imp_irpj_csll_vetor[idx_fin] += imp_atual * prop_irpj_csll
                                imp_outros_vetor[idx_fin] += imp_atual * prop_outros
                            
    for i in range(prazo):
        # Despesas (Marketing, Comercial, Adm)
        desp_mes_mkt = 0.0
        desp_mes_com = 0.0
        desp_mes_adm = 0.0
        
        has_mkt_curve = sum(mkt_dist) > 0
        has_com_curve = sum(com_dist) > 0
        has_adm_curve = sum(adm_desp_dist) > 0

        if has_mkt_curve: desp_mes_mkt += marketing * (mkt_dist[i] / 100.0)
        elif vendas_dist[i] > 0: desp_mes_mkt += marketing * (vendas_dist[i] / 100.0)

        if has_com_curve: desp_mes_com += comercial * (com_dist[i] / 100.0)
        elif vendas_dist[i] > 0: desp_mes_com += comercial * (vendas_dist[i] / 100.0)

        if has_adm_curve: desp_mes_adm += adm * (adm_desp_dist[i] / 100.0)
        elif vendas_dist[i] > 0: desp_mes_adm += adm * (vendas_dist[i] / 100.0)

        desp_mkt_vetor.append(desp_mes_mkt)
        desp_com_vetor.append(desp_mes_com)
        desp_adm_vetor.append(desp_mes_adm)
        
        total_desp = desp_mes_mkt + desp_mes_com + desp_mes_adm
        
        for idx_ext, d in enumerate(extra_mkt_dists):
            has_d_curve = sum(d["dist"]) > 0
            val_ext = 0.0
            if has_d_curve: val_ext = d["valor"] * (d["dist"][i] / 100.0)
            elif vendas_dist[i] > 0: val_ext = d["valor"] * (vendas_dist[i] / 100.0)
            desp_extra_vetors[idx_ext].append(val_ext)
            total_desp += val_ext

        desp_vetor.append(total_desp)

        # Obras e CAPEX (Infra, Projetos, Aquisição, Adm Obras)
        obr_mes_custo = 0.0
        obr_mes_proj = 0.0
        obr_mes_aq = 0.0
        obr_mes_adm = 0.0

        if obras_dist[i] > 0: obr_mes_custo += custo_obras * (obras_dist[i] / 100.0)

        has_proj_curve = sum(proj_dist) > 0
        has_aq_curve = sum(aq_dist) > 0
        has_adm_obr_curve = sum(adm_obr_dist) > 0

        if has_proj_curve: obr_mes_proj += custo_projetos * (proj_dist[i] / 100.0)
        elif obras_dist[i] > 0: obr_mes_proj += custo_projetos * (obras_dist[i] / 100.0)

        if has_aq_curve: obr_mes_aq += aquisicao_area * (aq_dist[i] / 100.0)
        elif obras_dist[i] > 0: obr_mes_aq += aquisicao_area * (obras_dist[i] / 100.0)

        if has_adm_obr_curve: obr_mes_adm += adm_obras * (adm_obr_dist[i] / 100.0)
        elif obras_dist[i] > 0: obr_mes_adm += adm_obras * (obras_dist[i] / 100.0)

        fator_incc = (1 + taxa_incc_mensal) ** i
        obr_custo_vetor.append(obr_mes_custo * fator_incc)
        obr_proj_vetor.append(obr_mes_proj * fator_incc)
        obr_aq_vetor.append(obr_mes_aq * fator_incc)
        obr_adm_vetor.append(obr_mes_adm * fator_incc)
        
        total_obr = (obr_mes_custo + obr_mes_proj + obr_mes_aq + obr_mes_adm) * fator_incc

        for idx_ext, d in enumerate(extra_obr_dists):
            has_d_curve = sum(d["dist"]) > 0
            val_ext = 0.0
            if has_d_curve: val_ext = d["valor"] * (d["dist"][i] / 100.0)
            elif obras_dist[i] > 0: val_ext = d["valor"] * (obras_dist[i] / 100.0)
            val_ext *= fator_incc
            obr_extra_vetors[idx_ext].append(val_ext)
            total_obr += val_ext

        obr_vetor.append(total_obr)

    # Fallback: se nenhuma curva foi configurada, distribui linearmente
    if sum(rec_vetor) == 0 and vgv_total > 0:
        linear_prazo = prazo - 1  # exclui o mês de CRI
        for i in range(linear_prazo):
            rec_val = vgv_total / linear_prazo
            imp_val = total_impostos / linear_prazo
            rec_vetor[i] = rec_val
            rec_vendas_vetor[i] = rec_val
            rec_entrada_vetor[i] = rec_val # Fallback places everything into entrada
            rec_parcelas_vetor[i] = 0.0
            rec_juros_vetor[i] = 0.0
            imp_vetor[i] = imp_val
            imp_pis_vetor[i] = imp_val * prop_pis
            imp_cofins_vetor[i] = imp_val * prop_cofins
            imp_irpj_csll_vetor[i] = imp_val * prop_irpj_csll
            imp_outros_vetor[i] = imp_val * prop_outros
            
            desp_vetor[i] = total_despesas / linear_prazo
            if i < len(desp_mkt_vetor): desp_mkt_vetor[i] = marketing / linear_prazo
            if i < len(desp_com_vetor): desp_com_vetor[i] = comercial / linear_prazo
            if i < len(desp_adm_vetor): desp_adm_vetor[i] = adm / linear_prazo
            for idx_ext, d in enumerate(extra_mkt_dists):
                if i < len(desp_extra_vetors[idx_ext]): desp_extra_vetors[idx_ext][i] = d["valor"] / linear_prazo
    
    if sum(obr_vetor) == 0 and custo_obras_total > 0:
        linear_prazo = prazo - 1
        for i in range(linear_prazo):
            fator_incc = (1 + taxa_incc_mensal) ** i
            val = (custo_obras_total / linear_prazo) * fator_incc
            obr_vetor[i] = val
            
            if i < len(obr_custo_vetor): obr_custo_vetor[i] = (custo_obras / linear_prazo) * fator_incc
            if i < len(obr_proj_vetor): obr_proj_vetor[i] = (custo_projetos / linear_prazo) * fator_incc
            if i < len(obr_aq_vetor): obr_aq_vetor[i] = (aquisicao_area / linear_prazo) * fator_incc
            if i < len(obr_adm_vetor): obr_adm_vetor[i] = (adm_obras / linear_prazo) * fator_incc
            for idx_ext, d in enumerate(extra_obr_dists):
                if i < len(obr_extra_vetors[idx_ext]): obr_extra_vetors[idx_ext][i] = (d["valor"] / linear_prazo) * fator_incc

    df["Receitas"] = rec_vetor
    df["Receitas_Vendas"] = rec_vendas_vetor
    df["Receitas_Entrada"] = rec_entrada_vetor
    df["Receitas_Parcelas"] = rec_parcelas_vetor
    df["Receitas_Juros"] = rec_juros_vetor
    
    df["Obras"] = obr_vetor
    df["Obras_Custo"] = obr_custo_vetor
    df["Obras_Proj"] = obr_proj_vetor
    df["Obras_Aq"] = obr_aq_vetor
    df["Obras_Adm"] = obr_adm_vetor
    for idx_ext, d in enumerate(extra_obr_dists):
        df[f"Obras_Extra_{idx_ext}"] = obr_extra_vetors[idx_ext]
        
    df["Despesas"] = desp_vetor
    df["Despesas_Mkt"] = desp_mkt_vetor
    df["Despesas_Com"] = desp_com_vetor
    df["Despesas_Adm"] = desp_adm_vetor
    for idx_ext, d in enumerate(extra_mkt_dists):
        df[f"Despesas_Extra_{idx_ext}"] = desp_extra_vetors[idx_ext]
    df["Impostos"] = imp_vetor
    df["Impostos_PIS"] = imp_pis_vetor
    df["Impostos_COFINS"] = imp_cofins_vetor
    df["Impostos_IRPJ_CSLL"] = imp_irpj_csll_vetor
    df["Impostos_Outros"] = imp_outros_vetor
    
    df["Terreno"] = 0.0
    df.loc[0, "Terreno"] = valor_terreno

    # Funding (CRI/CRA/Banco)
    df["Funding_Entrada"] = 0.0
    df["Funding_Despesas"] = 0.0      # tudo o que sai do caixa por causa do funding
    df["Funding_Amortizacao"] = 0.0   # parte de Funding_Despesas que é devolução do principal

    funding = phase.funding
    if funding and (funding.tipo_funding or "") != "Nenhum":
        volume, custo_estruturacao, custo_recorrente_total = calcular_custos_funding(db, funding, custo_obras_total, vgv_total)

        # A entrada do Funding (dinheiro captado)
        if volume > 0:
            df.loc[0, "Funding_Entrada"] = volume

        # Juros + devolução do principal (Banco e CRI/CRA), pelo sistema escolhido.
        if funding.tipo_funding in TIPOS_FUNDING_COM_CRONOGRAMA and volume > 0 and (funding.prazo_meses or 0) > 0:
            sis_amort = getattr(funding, 'sistema_amortizacao_banco', 'SAC') or 'SAC'
            parcelas = cronograma_funding(volume, taxa_mensal_funding(funding), funding.prazo_meses, sis_amort)
            ultimo_mes = len(parcelas)  # pagamentos nos meses 1..n (índice 0 é a captação)
            if ultimo_mes + 1 > len(df):
                # Parcelas além do horizonte: estende o fluxo com meses zerados em vez de descartá-las.
                novo_tam = ultimo_mes + 1
                df = df.reindex(range(novo_tam), fill_value=0.0)
                df["Mes"] = range(1, novo_tam + 1)
            for j, (juros, amort) in enumerate(parcelas):
                df.loc[1 + j, "Funding_Despesas"] += juros + amort
                df.loc[1 + j, "Funding_Amortizacao"] += amort

        # Custos de estruturação e recorrentes (CRI/CRA; no Banco são zero)
        custo_total_funding = custo_estruturacao + custo_recorrente_total
        if custo_total_funding > 0:
            if getattr(funding, 'diluir_custos', False):
                # Dilui nos meses da obra — normaliza para garantir que soma = custo_total_funding
                total_obras_perc = sum(obras_dist[i] for i in range(prazo) if obras_dist[i] > 0)
                if total_obras_perc > 0:
                    for i in range(prazo):
                        if obras_dist[i] > 0:
                            df.loc[i, "Funding_Despesas"] += custo_total_funding * (obras_dist[i] / total_obras_perc)
                else:
                    df.loc[0, "Funding_Despesas"] += custo_total_funding
            else:
                # Mês 1 (Desembolso upfront)
                df.loc[0, "Funding_Despesas"] += custo_total_funding

    df["Fluxo_de_Caixa"] = df["Receitas"] - df["Obras"] - df["Despesas"] - df["Impostos"] - df["Terreno"] + df["Funding_Entrada"] - df["Funding_Despesas"]

    # --- CÁLCULO DE INDICADORES (Helper) ---
    def calc_indicadores(df_calc):
        cf_array = df_calc["Fluxo_de_Caixa"].tolist()
        
        # TIR que não converge (fluxo sem troca de sinal, por exemplo) fica None: a tela mostra
        # "n/d" em vez de 0%, que parecia um resultado.
        tir_mensal = None
        tir_anual = None
        try:
            tir_mensal = npf.irr(cf_array)
            if tir_mensal is None or pd.isna(tir_mensal) or tir_mensal <= -1:
                tir_mensal = None
            else:
                tir_anual = ((1 + tir_mensal) ** 12 - 1) * 100
        except Exception:
            tir_mensal = None
            tir_anual = None

        tma_anual = (phase.viability.taxa_desconto_vpl / 100.0) if phase.viability and phase.viability.taxa_desconto_vpl else 0.12
        tma_mensal = (1 + tma_anual) ** (1/12) - 1
        vpl = npf.npv(tma_mensal, cf_array) if cf_array else 0.0
        
        try:
            mtir_mensal_val = npf.mirr(cf_array, finance_rate=tma_mensal, reinvest_rate=tma_mensal)
            mtir_anual = ((1 + mtir_mensal_val) ** 12 - 1) * 100 if mtir_mensal_val and not pd.isna(mtir_mensal_val) else 0.0
            mtir_mensal = mtir_mensal_val * 100 if mtir_mensal_val and not pd.isna(mtir_mensal_val) else 0.0
        except Exception:
            mtir_mensal = 0.0
            mtir_anual = 0.0

        df_calc["Caixa_Acumulado"] = df_calc["Fluxo_de_Caixa"].cumsum()
        
        exposicao_idx = df_calc["Caixa_Acumulado"].idxmin() if len(df_calc) > 0 else 0
        exposicao_maxima = df_calc["Caixa_Acumulado"].min() if len(df_calc) > 0 else 0.0
        if exposicao_maxima > 0:
            exposicao_maxima = 0.0
            
        periodo_exposicao = int(exposicao_idx) + 1 if len(df_calc) > 0 else 0
        vida = len(cf_array)
        
        payback = None
        caixa_acum_list = df_calc["Caixa_Acumulado"].tolist()
        for j in range(max(0, periodo_exposicao - 1), vida):
            if caixa_acum_list[j] >= 0:
                payback = j + 1
                break

        # Devolver o principal do funding é caixa, não custo: o lucro só desconta juros e taxas.
        custo_financeiro = df_calc["Funding_Despesas"].sum() - df_calc["Funding_Amortizacao"].sum()
        lucro_liquido = df_calc["Receitas"].sum() - df_calc["Obras"].sum() - df_calc["Despesas"].sum() - df_calc["Impostos"].sum() - df_calc["Terreno"].sum() - custo_financeiro
        vgv_calc = df_calc["Receitas"].sum()
        margem = (lucro_liquido / vgv_calc * 100) if vgv_calc > 0 else 0.0

        total_investimento = df_calc["Obras"].sum() + df_calc["Despesas"].sum() + df_calc["Terreno"].sum()
        vgv_global_bruto = vgv_bruto # We have vgv_bruto in scope!
        
        expo_inv = abs(exposicao_maxima) / total_investimento * 100 if total_investimento > 0 else 0.0
        expo_vgv = abs(exposicao_maxima) / vgv_global_bruto * 100 if vgv_global_bruto > 0 else 0.0
        
        retorno_com_juros = (lucro_liquido / total_investimento * 100) if total_investimento > 0 else 0.0
        
        receita_total = df_calc["Receitas"].sum()
        receita_vendas = df_calc["Receitas_Vendas"].sum()
        prop_vendas = (receita_vendas / receita_total) if receita_total > 0 else 1.0
        impostos_vendas = df_calc["Impostos"].sum() * prop_vendas
        
        lucro_sem_juros = receita_vendas - total_investimento - impostos_vendas - custo_financeiro
        retorno_sem_juros = (lucro_sem_juros / total_investimento * 100) if total_investimento > 0 else 0.0

        return {
            "vgv_total": vgv_calc,
            "custo_obras": df_calc["Obras"].sum(),
            # Linhas da DRE de obras, tiradas do próprio fluxo: somam exatamente "Obras".
            "dre_obras_infraestrutura": float(df_calc["Obras_Custo"].sum()),
            "dre_obras_projetos": float(df_calc["Obras_Proj"].sum()),
            "dre_obras_aquisicao": float(df_calc["Obras_Aq"].sum()),
            "dre_obras_adm": float(df_calc["Obras_Adm"].sum()),
            "dre_obras_extras": float(df_calc["Obras"].sum() - df_calc["Obras_Custo"].sum() - df_calc["Obras_Proj"].sum() - df_calc["Obras_Aq"].sum() - df_calc["Obras_Adm"].sum()),
            "custo_financeiro_funding": float(custo_financeiro),
            # Linhas da DRE de despesas, tiradas do fluxo (acompanham a visão de cada parceiro).
            "dre_despesas_marketing": float(df_calc["Despesas_Mkt"].sum()),
            "dre_despesas_comercial": float(df_calc["Despesas_Com"].sum()),
            "dre_despesas_adm": float(df_calc["Despesas_Adm"].sum()),
            "dre_despesas_extras": float(df_calc["Despesas"].sum() - df_calc["Despesas_Mkt"].sum() - df_calc["Despesas_Com"].sum() - df_calc["Despesas_Adm"].sum()),
            "custo_projetos": custo_projetos, # Fixos não escalonados aqui, DRE usa soma
            "aquisicao_area": aquisicao_area,
            "adm_obras": adm_obras,
            "marketing": marketing,
            "comercial": comercial,
            "comissao": 0.0,
            "adm_despesas": adm,
            "valor_terreno": df_calc["Terreno"].sum(),
            "impostos": df_calc["Impostos"].sum(),
            "extra_constructions_total": sum([e["valor"] for e in extra_constructions]) if 'extra_constructions' in locals() else 0.0,
            "extra_expenses_total": sum([e["valor"] for e in extra_expenses]) if 'extra_expenses' in locals() else 0.0,
            "lucro_liquido": lucro_liquido,
            "margem_perc": margem,
            "tir_aa": tir_anual,
            "tir_am": float(tir_mensal * 100) if tir_mensal is not None else None,
            "mtir_am": float(mtir_mensal),
            "mtir_aa": float(mtir_anual),
            "vpl": float(vpl) if not pd.isna(vpl) else 0.0,
            "tma_aa": float(tma_anual * 100),
            "exposicao_maxima": float(exposicao_maxima),
            "expo_inv": float(expo_inv),
            "expo_vgv": float(expo_vgv),
            "retorno_com_juros": float(retorno_com_juros),
            "retorno_sem_juros": float(retorno_sem_juros),
            "periodo_exposicao": periodo_exposicao,
            "payback": payback,
            "vida": vida
        }

    # Calcula Indicadores Globais
    ind_global = calc_indicadores(df)
    
    # --- VISÕES POR PARCEIRO (regra de 09/11/2026) ---
    # O percentual de cada parceiro vale sobre o projeto inteiro.
    # Receitas, impostos e funding: pelo percentual.
    # Custos marcados como rateados: pelo percentual.
    # Custos não rateados: 100% dos empreendedores, repartidos na proporção de cada um.
    abertura_json = getattr(phase.exchanges, "abertura_terrenistas_json", []) or []
    perc_inv = getattr(phase.exchanges, 'perc_parceria_investidor', 0.0) or 0.0

    parceiros = []
    for idx_parc, parceiro in enumerate(abertura_json):
        nome_base = (parceiro.get("nome") or f"Parceiro {idx_parc+1}").strip()
        tipo = parceiro.get("tipo") or "Proprietário"
        parceiros.append({
            "nome": f"{nome_base} ({tipo})",
            "tipo": tipo,
            "perc": (parceiro.get("percentual", 0.0) or 0.0) / 100.0,
        })
    soma_emp = sum(p["perc"] for p in parceiros if p["tipo"] == "Empreendedor")
    soma_total = sum(p["perc"] for p in parceiros)

    COLS_RECEITA = ["Receitas", "Receitas_Vendas", "Receitas_Entrada", "Receitas_Parcelas", "Receitas_Juros",
                    "Impostos", "Impostos_PIS", "Impostos_COFINS", "Impostos_IRPJ_CSLL", "Impostos_Outros",
                    "Funding_Entrada", "Funding_Despesas", "Funding_Amortizacao"]
    obras_rateio = [("Obras_Custo", "custo_obras"), ("Obras_Proj", "custo_projetos"),
                    ("Obras_Aq", "aquisicao_area"), ("Obras_Adm", "adm_obras")]
    obras_rateio += [(f"Obras_Extra_{i}", f"extra_obra_{i}") for i in range(len(extra_obr_dists))]
    desp_rateio = [("Despesas_Mkt", "marketing"), ("Despesas_Com", "comercial"), ("Despesas_Adm", "adm")]
    desp_rateio += [(f"Despesas_Extra_{i}", f"extra_despesa_{i}") for i in range(len(extra_mkt_dists))]

    def _visao(fator: float, fator_nao_rateado: float):
        """fator: participação no projeto; fator_nao_rateado: parte dos custos não rateados."""
        dv = df.copy()
        for col in COLS_RECEITA:
            if col in dv.columns:
                dv[col] = df[col] * fator

        def _f(chave):
            return fator if rateios.get(chave, False) else fator_nao_rateado

        def _agrupa(total_col, partes, chave_resto):
            soma_partes = 0.0
            for col, chave in partes:
                if col in dv.columns:
                    dv[col] = df[col] * _f(chave)
                    soma_partes = soma_partes + dv[col]
            # Sobra que não está em nenhuma sub-coluna segue a regra do primeiro item
            resto = df[total_col] - sum(df[c] for c, _ in partes if c in df.columns)
            dv[total_col] = soma_partes + resto * _f(chave_resto)

        _agrupa("Obras", obras_rateio, "custo_obras")
        _agrupa("Despesas", desp_rateio, "marketing")
        dv["Terreno"] = df["Terreno"] * _f("aquisicao_area")
        dv["Fluxo_de_Caixa"] = dv["Receitas"] - dv["Obras"] - dv["Despesas"] - dv["Impostos"] - dv["Terreno"] + dv["Funding_Entrada"] - dv["Funding_Despesas"]
        return dv

    # --- VISÃO EMPREENDEDOR ---
    # Soma dos empreendedores da abertura; sem empreendedor na abertura, o que sobra
    # depois de Proprietário e Investidor (como antes).
    if parceiros and soma_emp > 0:
        fator_emp = soma_emp
    else:
        fator_emp = max(0.0, 1.0 - (perc_terr + perc_inv) / 100.0)
    df_emp = _visao(fator_emp, 1.0)
    ind_empreendedor = calc_indicadores(df_emp)

    # --- VISÕES INDIVIDUAIS DE PARCEIROS ---
    monthly_cashflow_parceiros = {}
    indicators_parceiros = {}
    for p in parceiros:
        nao_rateado = (p["perc"] / soma_emp) if (p["tipo"] == "Empreendedor" and soma_emp > 0) else 0.0
        df_p = _visao(p["perc"], nao_rateado)
        indicators_parceiros[p["nome"]] = calc_indicadores(df_p)
        monthly_cashflow_parceiros[p["nome"]] = df_p.to_dict(orient="records")

    aviso_parceiros = None
    if parceiros and abs(soma_total - 1.0) > 1e-6:
        aviso_parceiros = f"A abertura de parceiros soma {soma_total * 100:.2f}% do projeto (deveria somar 100%)."
    elif parceiros and soma_emp <= 0:
        aviso_parceiros = "Não há empreendedor na abertura: os custos não rateados não ficam com nenhum parceiro."

    return {
        "indicators": ind_global,
        "indicators_empreendedor": ind_empreendedor,
        "monthly_cashflow": df.to_dict(orient="records"),
        "monthly_cashflow_empreendedor": df_emp.to_dict(orient="records"),
        "monthly_cashflow_parceiros": monthly_cashflow_parceiros,
        "indicators_parceiros": indicators_parceiros,
        "aviso_parceiros": aviso_parceiros,
        "phase": {
            "revenue": {
                "condicoes_pagamento_json": phase.revenue.condicoes_pagamento_json if phase.revenue else [],
                "velocidade_vendas_json": phase.revenue.velocidade_vendas_json if phase.revenue else [],
                "taxa_juros_vendas": float(phase.revenue.taxa_juros_vendas) if phase.revenue and getattr(phase.revenue, "taxa_juros_vendas", None) else 0.0,
            },
            "expenses": {
                "comissao_corretagem_valor": getattr(phase.expenses, 'comissao_corretagem_valor', 0.0) if phase.expenses else 0.0,
                "marketing_valor": getattr(phase.expenses, 'marketing_valor', 0.0) if phase.expenses else 0.0,
                "marketing_tipo": getattr(phase.expenses, 'marketing_tipo', '%') if phase.expenses else '%',
                "adm_valor": getattr(phase.expenses, 'adm_valor', 0.0) if phase.expenses else 0.0,
                "adm_tipo": getattr(phase.expenses, 'adm_tipo', '%') if phase.expenses else '%',
                "comercial_valor": getattr(phase.expenses, 'comercial_valor', 0.0) if phase.expenses else 0.0,
                "comercial_tipo": getattr(phase.expenses, 'comercial_tipo', '%') if phase.expenses else '%',
                "extra_expenses_json": getattr(phase.expenses, 'extra_expenses_json', []) if phase.expenses else []
            },
            "taxes": {
                "aliquota_total": aliquota_imposto if 'aliquota_imposto' in locals() else (getattr(phase.taxes, 'aliquota_total', 4.0) if phase.taxes else 4.0),
            },
            "construction": {
                "custo_projetos": getattr(phase.construction, 'custo_projetos', 0.0) if phase.construction else 0.0,
                "custo_projetos_tipo": getattr(phase.construction, 'custo_projetos_tipo', '%') if phase.construction else '%',
            }
        },
        "_debug": {
            "sistema_amortizacao": sistema_amortizacao,
            "taxa_juros": taxa_juros,
            "taxa_juros_decimal": taxa_juros_decimal,
            "taxa_inf": taxa_inf,
            "taxa_inf_mensal": taxa_inf_mensal,
            "sum_vendas_dist_before_fallback": sum(vendas_dist),
            "sum_rec_vetor": sum(rec_vetor),
            "sum_rec_vendas_vetor": sum(rec_vendas_vetor),
            "sum_rec_juros_vetor": sum(rec_juros_vetor),
            "max_inst": max_inst,
            "prazo": prazo,
            "num_condicoes": len(condicoes),
            "condicoes_com_juros": [c for c in condicoes if c.get("aplica_juros")],
            "vgv_total": vgv_total,
        }
    }
