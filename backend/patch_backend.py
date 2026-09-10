import sys

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend/app/services/math_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if '    # Indicadores Matemáticos' in line:
        break
    new_lines.append(line)

rest_of_file = """    # --- CÁLCULO DE INDICADORES (Helper) ---
    def calc_indicadores(df_calc):
        cf_array = df_calc["Fluxo_de_Caixa"].tolist()
        
        tir_mensal = 0.0
        tir_anual = 0.0
        try:
            tir_mensal = npf.irr(cf_array)
            tir_anual = ((1 + tir_mensal) ** 12 - 1) * 100 if tir_mensal is not None and not pd.isna(tir_mensal) and tir_mensal > -1 else 0.0
        except Exception:
            tir_mensal = 0.0
            tir_anual = 0.0

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

        lucro_liquido = df_calc["Receitas"].sum() - df_calc["Obras"].sum() - df_calc["Despesas"].sum() - df_calc["Impostos"].sum() - df_calc["Terreno"].sum() - df_calc["Funding_Despesas"].sum()
        vgv_calc = df_calc["Receitas"].sum()
        margem = (lucro_liquido / vgv_calc * 100) if vgv_calc > 0 else 0.0

        return {
            "vgv_total": vgv_calc,
            "custo_obras": df_calc["Obras"].sum(),
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
            "tir_am": float(tir_mensal * 100) if tir_mensal is not None and not pd.isna(tir_mensal) and tir_mensal > -1 else 0.0,
            "mtir_am": float(mtir_mensal),
            "mtir_aa": float(mtir_anual),
            "vpl": float(vpl) if not pd.isna(vpl) else 0.0,
            "tma_aa": float(tma_anual * 100),
            "exposicao_maxima": float(exposicao_maxima),
            "periodo_exposicao": periodo_exposicao,
            "payback": payback,
            "vida": vida
        }

    # Calcula Indicadores Globais
    ind_global = calc_indicadores(df)
    
    # --- VISÃO EMPREENDEDOR ---
    df_emp = df.copy()
    if perc_terr > 0:
        df_emp["Receitas"] *= fator_empreendedor
        df_emp["Receitas_Vendas"] *= fator_empreendedor
        df_emp["Receitas_Juros"] *= fator_empreendedor
        df_emp["Impostos"] *= fator_empreendedor
        df_emp["Impostos_PIS"] *= fator_empreendedor
        df_emp["Impostos_COFINS"] *= fator_empreendedor
        df_emp["Impostos_IRPJ_CSLL"] *= fator_empreendedor
        df_emp["Impostos_Outros"] *= fator_empreendedor
        
        if rateios.get("custo_obras", False):
            df_emp["Obras"] *= fator_empreendedor
            
        if rateios.get("marketing", False):
            df_emp["Despesas"] *= fator_empreendedor
            
        df_emp["Fluxo_de_Caixa"] = df_emp["Receitas"] - df_emp["Obras"] - df_emp["Despesas"] - df_emp["Impostos"] - df_emp["Terreno"] + df_emp["Funding_Entrada"] - df_emp["Funding_Despesas"]
    
    ind_empreendedor = calc_indicadores(df_emp)

    return {
        "indicators": ind_global,
        "indicators_empreendedor": ind_empreendedor,
        "monthly_cashflow": df.to_dict(orient="records"),
        "monthly_cashflow_empreendedor": df_emp.to_dict(orient="records"),
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
"""
new_lines.append(rest_of_file)

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend/app/services/math_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
