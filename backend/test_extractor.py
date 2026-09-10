import sys
sys.path.append('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
from app.services.carga_inicial_sharepoint import parse_sienge_report
with open('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/V10_RES CEN PARQUE II.xlsb', 'rb') as f:
    content = f.read()
res = parse_sienge_report(content)
print(len(res), 'rows found')
if len(res)>0: print(res[0])
