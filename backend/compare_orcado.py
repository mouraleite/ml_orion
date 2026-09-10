import pandas as pd
import sqlite3
import json

df = pd.read_excel('../Agrupamento empresa 1 - aberto.xlsx', skiprows=11)
excel_orcado = {}

for idx, row in df.iterrows():
    try:
        conta = str(row['Conta']).strip()
        val_jan_orc = row.get('Orçado', 0.0)
        
        if pd.isna(conta) or conta == 'nan' or conta == 'Total Geral':
            continue
            
        if pd.isna(val_jan_orc):
            val_jan_orc = 0.0
            
        excel_orcado[conta] = val_jan_orc
    except Exception as e:
        continue

conn = sqlite3.connect('viabilidades.db')
c = conn.cursor()

c.execute('SELECT id, custom_data FROM cost_centers')
cc_emp1 = []
for row in c.fetchall():
    try:
        custom = json.loads(row[1]) if row[1] else {}
        if str(custom.get('__id_empresa')) == '1':
            cc_emp1.append(row[0])
    except:
        pass
cc_in = ','.join(map(str, cc_emp1))

c.execute('SELECT id, name, fl_redutora FROM planos_financeiros')
planos = {row[0]: {'name': row[1], 'fl_redutora': row[2]} for row in c.fetchall()}

query = f'''
    SELECT plano_financeiro_id, SUM(jan) 
    FROM orcamento_itens 
    JOIN orcamentos ON orcamentos.id = orcamento_itens.orcamento_id
    WHERE orcamento_itens.produto_id IN ({cc_in})
      AND orcamentos.ano = 2026
      AND orcamentos.tipo = 'DESPESAS'
      AND orcamentos.status IN ('Aprovado', 'Fechado')
    GROUP BY plano_financeiro_id
'''
try:
    c.execute(query)
    rows = c.fetchall()
except Exception as e:
    print('Failed query orcamentos:', e)
    rows = []

db_orcado = {}

for row in rows:
    p_id = row[0]
    val = row[1] or 0.0
    p = planos.get(p_id, {})
    name = str(p.get('name', '')).strip()
    fl = str(p.get('fl_redutora', '')).strip().upper()
    
    if fl == 'S' or 'reten' in name.lower():
        val = -abs(val)
        
    db_orcado[name] = db_orcado.get(name, 0.0) + val

diffs = []
all_cats = set(excel_orcado.keys()).union(set(db_orcado.keys()))

for cat in all_cats:
    e_val = excel_orcado.get(cat, 0.0)
    d_val = db_orcado.get(cat, 0.0)
    diff = round(d_val - e_val, 2)
    
    if abs(diff) > 1.0:
        diffs.append((cat, d_val, e_val, diff))

diffs.sort(key=lambda x: abs(x[3]), reverse=True)

with open('diffs_orcado.txt', 'w', encoding='utf-8') as out:
    for d in diffs:
        out.write(f'- {d[0]}: Sienge {d[2]} | DB {d[1]:.2f} | Diff {d[3]:.2f}\n')

print(f"Found {len(diffs)} differences.")
