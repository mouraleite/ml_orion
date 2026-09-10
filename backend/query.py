import sqlite3, json

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

total_orcado = 0.0
total_redutoras = 0.0

for row in rows:
    p_id = row[0]
    val = row[1] or 0.0
    p = planos.get(p_id, {})
    name = str(p.get('name', '')).lower()
    fl = str(p.get('fl_redutora', '')).strip().upper()
    
    if fl == 'S' or 'reten' in name:
        total_redutoras += val
        val = -abs(val)
        
    total_orcado += val

print('Total Jan Orcado from SQL:', total_orcado)
print('Total Jan Redutoras:', total_redutoras)
