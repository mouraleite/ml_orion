import re

path = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend/app/services/math_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace initialization
content = content.replace('    obr_vetor = []\n    desp_vetor = []', '''    obr_vetor = []
    obr_custo_vetor = []
    obr_proj_vetor = []
    obr_aq_vetor = []
    obr_adm_vetor = []
    obr_extra_vetors = [[] for _ in extra_obr_dists]
    
    desp_vetor = []
    desp_mkt_vetor = []
    desp_com_vetor = []
    desp_adm_vetor = []
    desp_extra_vetors = [[] for _ in extra_mkt_dists]''')

# Replace loop body
old_loop = """        # Despesas (Marketing, Comercial, Adm)
        desp_mes = 0.0
        has_mkt_curve = sum(mkt_dist) > 0
        has_com_curve = sum(com_dist) > 0
        has_adm_curve = sum(adm_desp_dist) > 0

        if has_mkt_curve:
            desp_mes += marketing * (mkt_dist[i] / 100.0)
        elif vendas_dist[i] > 0:
            desp_mes += marketing * (vendas_dist[i] / 100.0)

        if has_com_curve:
            desp_mes += comercial * (com_dist[i] / 100.0)
        elif vendas_dist[i] > 0:
            desp_mes += comercial * (vendas_dist[i] / 100.0)

        if has_adm_curve:
            desp_mes += adm * (adm_desp_dist[i] / 100.0)
        elif vendas_dist[i] > 0:
            desp_mes += adm * (vendas_dist[i] / 100.0)

        # comissao é descontada diretamente do VGV e não entra na DRE como despesa
        # if vendas_dist[i] > 0:
        #     desp_mes += comissao * (vendas_dist[i] / 100.0)

        for d in extra_mkt_dists:
            has_d_curve = sum(d["dist"]) > 0
            if has_d_curve:
                desp_mes += d["valor"] * (d["dist"][i] / 100.0)
            elif vendas_dist[i] > 0:
                desp_mes += d["valor"] * (vendas_dist[i] / 100.0)

        desp_vetor.append(desp_mes)

        # Obras e CAPEX (Infra, Projetos, Aquisição, Adm Obras)
        obr_mes = 0.0
        if obras_dist[i] > 0:
            obr_mes += custo_obras * (obras_dist[i] / 100.0)

        has_proj_curve = sum(proj_dist) > 0
        has_aq_curve = sum(aq_dist) > 0
        has_adm_obr_curve = sum(adm_obr_dist) > 0

        if has_proj_curve:
            obr_mes += custo_projetos * (proj_dist[i] / 100.0)
        elif obras_dist[i] > 0:
            obr_mes += custo_projetos * (obras_dist[i] / 100.0)

        if has_aq_curve:
            obr_mes += aquisicao_area * (aq_dist[i] / 100.0)
        elif obras_dist[i] > 0:
            obr_mes += aquisicao_area * (obras_dist[i] / 100.0)

        if has_adm_obr_curve:
            obr_mes += adm_obras * (adm_obr_dist[i] / 100.0)
        elif obras_dist[i] > 0:
            obr_mes += adm_obras * (obras_dist[i] / 100.0)

        for d in extra_obr_dists:
            has_d_curve = sum(d["dist"]) > 0
            if has_d_curve:
                obr_mes += d["valor"] * (d["dist"][i] / 100.0)
            elif obras_dist[i] > 0:
                obr_mes += d["valor"] * (obras_dist[i] / 100.0)

        fator_incc = (1 + taxa_incc_mensal) ** i
        obr_vetor.append(obr_mes * fator_incc)"""

new_loop = """        # Despesas (Marketing, Comercial, Adm)
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

        obr_vetor.append(total_obr)"""

content = content.replace(old_loop, new_loop)

# Fallback modifications
old_fallback = """    # Fallback: se nenhuma curva foi configurada, distribui linearmente
    if sum(rec_vetor) == 0 and vgv_total > 0:
        linear_prazo = prazo - 1  # exclui o mês de CRI
        for i in range(linear_prazo):
            rec_val = vgv_total / linear_prazo
            imp_val = total_impostos / linear_prazo
            rec_vetor[i] = rec_val
            # Preenche os vetores desagregados de receita
            rec_vendas_vetor[i] = rec_val   # sem juros no fallback linear
            rec_juros_vetor[i] = 0.0
            # Preenche os vetores desagregados de impostos
            imp_vetor[i] = imp_val
            imp_pis_vetor[i] = imp_val * prop_pis
            imp_cofins_vetor[i] = imp_val * prop_cofins
            imp_irpj_csll_vetor[i] = imp_val * prop_irpj_csll
            imp_outros_vetor[i] = imp_val * prop_outros
            desp_vetor[i] = total_despesas / linear_prazo
    
    if sum(obr_vetor) == 0 and custo_obras_total > 0:
        linear_prazo = prazo - 1
        for i in range(linear_prazo):
            fator_incc = (1 + taxa_incc_mensal) ** i
            obr_vetor[i] = (custo_obras_total / linear_prazo) * fator_incc"""

new_fallback = """    # Fallback: se nenhuma curva foi configurada, distribui linearmente
    if sum(rec_vetor) == 0 and vgv_total > 0:
        linear_prazo = prazo - 1  # exclui o mês de CRI
        for i in range(linear_prazo):
            rec_val = vgv_total / linear_prazo
            imp_val = total_impostos / linear_prazo
            rec_vetor[i] = rec_val
            rec_vendas_vetor[i] = rec_val
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
                if i < len(obr_extra_vetors[idx_ext]): obr_extra_vetors[idx_ext][i] = (d["valor"] / linear_prazo) * fator_incc"""

content = content.replace(old_fallback, new_fallback)

# Assign to df
old_assign = """    df["Obras"] = obr_vetor
    df["Despesas"] = desp_vetor"""
new_assign = """    df["Obras"] = obr_vetor
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
        df[f"Despesas_Extra_{idx_ext}"] = desp_extra_vetors[idx_ext]"""

content = content.replace(old_assign, new_assign)

# Add partner logic at the end
old_return = """    return {
        "indicators": ind_global,
        "indicators_empreendedor": ind_empreendedor,
        "monthly_cashflow": df.to_dict(orient="records"),
        "monthly_cashflow_empreendedor": df_emp.to_dict(orient="records"),
        "_debug": {"""

new_return = """    # --- VISÕES INDIVIDUAIS DE PARCEIROS ---
    monthly_cashflow_parceiros = {}
    indicators_parceiros = {}
    
    abertura_json = getattr(phase.exchanges, "abertura_terrenistas_json", []) or []
    
    for idx_parc, parceiro in enumerate(abertura_json):
        nome = parceiro.get("nome", f"Parceiro {idx_parc+1}")
        tipo = parceiro.get("tipo", "Proprietário")
        perc = parceiro.get("percentual", 0.0) / 100.0
        
        # Matematica igual ao Excel: percentual do grupo * percentual dele
        if tipo == "Proprietário":
            perc_grupo = (perc_terr / 100.0) if perc_terr > 0 else 0.0
        elif tipo == "Investidor":
            perc_grupo = (perc_inv / 100.0) if perc_inv > 0 else 0.0
        elif tipo == "Empreendedor":
            perc_grupo = (perc_emp / 100.0) if perc_emp > 0 else 0.0
        else:
            perc_grupo = 0.0
            
        fator_grupo = perc
        fator_global = perc_grupo * perc
        
        df_p = df.copy()
        
        df_p["Receitas"] *= fator_global
        df_p["Receitas_Vendas"] *= fator_global
        df_p["Receitas_Juros"] *= fator_global
        df_p["Impostos"] *= fator_global
        df_p["Impostos_PIS"] *= fator_global
        df_p["Impostos_COFINS"] *= fator_global
        df_p["Impostos_IRPJ_CSLL"] *= fator_global
        df_p["Impostos_Outros"] *= fator_global
        
        def calc_obra(col, is_rateado):
            if is_rateado: return df[col] * fator_global
            else: return df[col] * perc if tipo == "Empreendedor" else 0.0
                
        df_p["Obras_Custo"] = calc_obra("Obras_Custo", rateios.get("custo_obras", False))
        df_p["Obras_Proj"] = calc_obra("Obras_Proj", rateios.get("custo_projetos", False))
        df_p["Obras_Aq"] = calc_obra("Obras_Aq", rateios.get("aquisicao_area", False))
        df_p["Obras_Adm"] = calc_obra("Obras_Adm", rateios.get("adm_obras", False))
        
        total_obras = df_p["Obras_Custo"] + df_p["Obras_Proj"] + df_p["Obras_Aq"] + df_p["Obras_Adm"]
        for idx_ext, d in enumerate(extra_obr_dists):
            if f"Obras_Extra_{idx_ext}" in df.columns:
                df_p[f"Obras_Extra_{idx_ext}"] = calc_obra(f"Obras_Extra_{idx_ext}", rateios.get(f"extra_obra_{idx_ext}", False))
                total_obras += df_p[f"Obras_Extra_{idx_ext}"]
        
        df_p["Obras"] = total_obras
        
        def calc_desp(col, is_rateado):
            if is_rateado: return df[col] * fator_global
            else: return df[col] * perc if tipo == "Empreendedor" else 0.0
                
        df_p["Despesas_Mkt"] = calc_desp("Despesas_Mkt", rateios.get("marketing", False))
        df_p["Despesas_Com"] = calc_desp("Despesas_Com", rateios.get("comercial", False))
        df_p["Despesas_Adm"] = calc_desp("Despesas_Adm", rateios.get("adm", False))
        
        total_desp = df_p["Despesas_Mkt"] + df_p["Despesas_Com"] + df_p["Despesas_Adm"]
        for idx_ext, d in enumerate(extra_mkt_dists):
            if f"Despesas_Extra_{idx_ext}" in df.columns:
                df_p[f"Despesas_Extra_{idx_ext}"] = calc_desp(f"Despesas_Extra_{idx_ext}", rateios.get(f"extra_despesa_{idx_ext}", False))
                total_desp += df_p[f"Despesas_Extra_{idx_ext}"]
            
        df_p["Despesas"] = total_desp
        
        if rateios.get("aquisicao_area", False):
            df_p["Terreno"] = df["Terreno"] * fator_global
        else:
            df_p["Terreno"] = df["Terreno"] * perc if tipo == "Empreendedor" else 0.0
            
        df_p["Funding_Entrada"] *= fator_global
        df_p["Funding_Despesas"] *= fator_global
        
        df_p["Fluxo_de_Caixa"] = df_p["Receitas"] - df_p["Obras"] - df_p["Despesas"] - df_p["Impostos"] - df_p["Terreno"] + df_p["Funding_Entrada"] - df_p["Funding_Despesas"]
        
        ind_p = calc_indicadores(df_p)
        monthly_cashflow_parceiros[nome] = df_p.to_dict(orient="records")
        indicators_parceiros[nome] = ind_p
        
    return {
        "indicators": ind_global,
        "indicators_empreendedor": ind_empreendedor,
        "monthly_cashflow": df.to_dict(orient="records"),
        "monthly_cashflow_empreendedor": df_emp.to_dict(orient="records"),
        "monthly_cashflow_parceiros": monthly_cashflow_parceiros,
        "indicators_parceiros": indicators_parceiros,
        "_debug": {"""

content = content.replace(old_return, new_return)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
