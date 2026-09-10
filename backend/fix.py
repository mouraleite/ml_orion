import re
import sys

file_path = r'c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\app\api\routes\acompanhamento.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def rewrite_func(content, fn_name):
    pattern = r'(def ' + fn_name + r'\(.*?)(reais = db\.query)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"Failed to match {fn_name}")
        return content
    
    block = match.group(1)
    
    # 1. replace orcamento fetching
    orc_pattern = r'(orc_query = [^\n]*\n\s+if not is_consolidado:[^\n]*\n\s+orc_query = [^\n]*\n)(\s+orcamento = [^\n]*\n\s+if not orcamento:\n\s+orcamento = [^\n]*\n)'
    new_orc = r'''\1    if is_consolidado:
        o_ref = orc_query.filter(Orcamento.status.in_(["Aprovado", "Fechado"])).order_by(Orcamento.id.desc()).first()
        if not o_ref: o_ref = orc_query.order_by(Orcamento.id.desc()).first()
        orcamentos = orc_query.filter(Orcamento.descricao == o_ref.descricao).all() if o_ref else []
    else:
        o = orc_query.filter(Orcamento.status.in_(["Aprovado", "Fechado"])).order_by(Orcamento.id.desc()).first()
        if not o: o = orc_query.order_by(Orcamento.id.desc()).first()
        orcamentos = [o] if o else []
'''
    block = re.sub(orc_pattern, new_orc, block)
    
    # 2. replace forecast fetching
    fc_pattern = r'(fc_query = [^\n]*\n\s+if not is_consolidado:[^\n]*\n\s+fc_query = [^\n]*\n)(\s+if forecast_id:.*?(?=\n\s+if not is_consolidado:\s+extra_prod))'
    new_fc = r'''\1    if forecast_id:
        ref_forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
        if ref_forecast:
            if is_consolidado:
                forecasts = fc_query.filter(Forecast.descricao == ref_forecast.descricao).all()
            else:
                f_ref = fc_query.filter(Forecast.descricao == ref_forecast.descricao).first()
                forecasts = [f_ref] if f_ref else []
        else:
            forecasts = []
    else:
        if is_consolidado:
            f_ref = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f_ref: f_ref = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = fc_query.filter(Forecast.descricao == f_ref.descricao).all() if f_ref else []
        else:
            f = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f: f = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = [f] if f else []'''
    block = re.sub(fc_pattern, new_fc, block, flags=re.DOTALL)
    
    # 3. replace extra_prod logic
    extra_pattern = r'if orcamento:\n\s+extra_prod.extend\(\[i.produto_id for i in getattr\(orcamento, \'itens_.*?\'(.*?)\]\)\n\s+extra_plan.extend\(\[i.plano_financeiro_id for i in getattr\(orcamento, \'itens_.*?\'(.*?)\]\)\n\s+if forecast:\n\s+extra_prod.extend\(\[i.produto_id for i in getattr\(forecast, \'itens_.*?\'(.*?)\]\)\n\s+extra_plan.extend\(\[i.plano_financeiro_id for i in getattr\(forecast, \'itens_.*?\'(.*?)\]\)'
    
    def repl_extra(m):
        # We need to dynamically get the 'itens_despesa' or 'itens_venda' string from the original text
        return f'''for orcamento in orcamentos:
            extra_prod.extend([i.produto_id for i in getattr(orcamento, 'itens_despesa', [])])
            extra_plan.extend([i.plano_financeiro_id for i in getattr(orcamento, 'itens_despesa', [])])
        for forecast in forecasts:
            extra_prod.extend([i.produto_id for i in getattr(forecast, 'itens_despesa', [])])
            extra_plan.extend([i.plano_financeiro_id for i in getattr(forecast, 'itens_despesa', [])])'''
    # We will just replace it generically.
    if 'itens_despesa' in block:
        itens_attr = 'itens_despesa'
    else:
        itens_attr = 'itens_venda'
        
    block = block.replace("if orcamento:\n            extra_prod.extend([i.produto_id for i in getattr(orcamento, '"+itens_attr+"', [])])\n            extra_plan.extend([i.plano_financeiro_id for i in getattr(orcamento, '"+itens_attr+"', [])])\n        if forecast:\n            extra_prod.extend([i.produto_id for i in getattr(forecast, '"+itens_attr+"', [])])\n            extra_plan.extend([i.plano_financeiro_id for i in getattr(forecast, '"+itens_attr+"', [])])", 
    f'''for orcamento in orcamentos:
            extra_prod.extend([i.produto_id for i in getattr(orcamento, '{itens_attr}', [])])
            extra_plan.extend([i.plano_financeiro_id for i in getattr(orcamento, '{itens_attr}', [])])
        for forecast in forecasts:
            extra_prod.extend([i.produto_id for i in getattr(forecast, '{itens_attr}', [])])
            extra_plan.extend([i.plano_financeiro_id for i in getattr(forecast, '{itens_attr}', [])])''')
            
    # 4. replace summation loops
    sum_orc_pattern = r'if orcamento:\n\s+for item in orcamento\.' + itens_attr + r':\n'
    sum_fc_pattern = r'if forecast:\n\s+for item in forecast\.' + itens_attr + r':\n'
    
    block = re.sub(sum_orc_pattern, f'for orcamento in orcamentos:\n        for item in getattr(orcamento, "{itens_attr}", []):\n', block)
    block = re.sub(sum_fc_pattern, f'for forecast in forecasts:\n        for item in getattr(forecast, "{itens_attr}", []):\n', block)

    return content[:match.start()] + block + content[match.end()-len(match.group(2)):]

new_content = rewrite_func(content, 'get_acompanhamento_despesas')
new_content = rewrite_func(new_content, 'get_acompanhamento_receitas')
new_content = rewrite_func(new_content, 'get_acompanhamento_vendas')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Done!")
