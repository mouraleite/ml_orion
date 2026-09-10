import json
import sqlite3

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

query = f'''
    SELECT category, SUM(value) 
    FROM actual_transactions 
    WHERE cost_center_id IN ({cc_in})
      AND transaction_date >= '2026-01-01'
      AND transaction_date <= '2026-01-31'
      AND transaction_type = 'OUTCOME'
      AND source_id LIKE 'SP-MIG-%'
      AND is_forecast = 0
    GROUP BY category
'''
c.execute(query)
db_txs = c.fetchall()

c.execute('SELECT name, fl_redutora FROM planos_financeiros')
fl_redutora = {row[0]: row[1] for row in c.fetchall()}
conn.close()

db_plans_totals = {}
for cat, val in db_txs:
    val = val or 0.0
    if str(fl_redutora.get(cat)).strip().upper() == 'S':
        val = -val
    cat = str(cat).strip()
    db_plans_totals[cat] = val

with open('excel_plans_full.json', 'r', encoding='utf-8') as f:
    excel_plans = json.load(f)

diffs = []
for cat, d_val in db_plans_totals.items():
    e_val = excel_plans.get(cat, 0.0)
    diff = round(d_val - e_val, 2)
    if abs(diff) > 1.0:
        diffs.append((cat, d_val, e_val, diff))

diffs.sort(key=lambda x: abs(x[3]), reverse=True)
with open('diffs_output.txt', 'w', encoding='utf-8') as out:
    out.write('=== CONTAS NO BANCO DE DADOS MAS QUE ESTÃO FALTANDO/DIFERENTES NO SIENGE ===\n')
    for d in diffs:
        out.write(f'- {d[0]}: Sienge tem R$ {d[2]}, mas Sistema importou R$ {d[1]:.2f} (Diferença: {d[3]:.2f})\n')
