import sys
import re

file_path = r'c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\app\api\routes\acompanhamento.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def rewrite_endpoint(content, fn_name, tipo):
    pattern = r'(def ' + fn_name + r'\(.*?)(if forecast_id:.*?(?=\n\s+if not is_consolidado:\s+extra_prod))'
    match = re.search(pattern, content, re.DOTALL)
    if not match: return content
    
    block = match.group(2)
    new_block = f'''if forecast_id:
        ref_forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
        if ref_forecast:
            if is_consolidado:
                forecasts = fc_query.filter(Forecast.descricao == ref_forecast.descricao).all()
            else:
                f_ref = db.query(Forecast).filter(
                    Forecast.ano == ano, 
                    Forecast.tipo == '{tipo}', 
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
            f = fc_query.filter(Forecast.status.in_(["Aprovado", "Fechado"])).order_by(Forecast.id.desc()).first()
            if not f: f = fc_query.order_by(Forecast.id.desc()).first()
            forecasts = [f] if f else []'''
            
    content = content[:match.start(2)] + new_block + content[match.end(2):]
    return content

c = rewrite_endpoint(content, 'get_acompanhamento_despesas', 'DESPESAS')
c = rewrite_endpoint(c, 'get_acompanhamento_receitas', 'RECEITAS')
c = rewrite_endpoint(c, 'get_acompanhamento_vendas', 'VENDAS')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(c)
print("Done!")
