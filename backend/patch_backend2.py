import re

path = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend/app/services/math_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find calc_indicadores and inject the 4 new variables
# It returns a dictionary at the end of calc_indicadores

new_vars = """        total_investimento = df_calc["Obras"].sum() + df_calc["Despesas"].sum() + df_calc["Terreno"].sum()
        vgv_global_bruto = vgv_bruto # We have vgv_bruto in scope!
        
        expo_inv = abs(exposicao_maxima) / total_investimento * 100 if total_investimento > 0 else 0.0
        expo_vgv = abs(exposicao_maxima) / vgv_global_bruto * 100 if vgv_global_bruto > 0 else 0.0
        
        retorno_com_juros = (lucro_liquido / total_investimento * 100) if total_investimento > 0 else 0.0
        
        receita_total = df_calc["Receitas"].sum()
        receita_vendas = df_calc["Receitas_Vendas"].sum()
        prop_vendas = (receita_vendas / receita_total) if receita_total > 0 else 1.0
        impostos_vendas = df_calc["Impostos"].sum() * prop_vendas
        
        lucro_sem_juros = receita_vendas - total_investimento - impostos_vendas - df_calc["Funding_Despesas"].sum()
        retorno_sem_juros = (lucro_sem_juros / total_investimento * 100) if total_investimento > 0 else 0.0
"""

# Find the end of calc_indicadores just before the return { ... }
target_string = "        return {"

content = content.replace(target_string, new_vars + "\n" + target_string)

# Now inject the new keys into the return dict
return_dict_add = """            "expo_inv": float(expo_inv),
            "expo_vgv": float(expo_vgv),
            "retorno_com_juros": float(retorno_com_juros),
            "retorno_sem_juros": float(retorno_sem_juros),"""

content = content.replace('"exposicao_maxima": float(exposicao_maxima),', '"exposicao_maxima": float(exposicao_maxima),\n' + return_dict_add)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
