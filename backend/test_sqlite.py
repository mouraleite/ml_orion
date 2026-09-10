import sqlite3
import json
conn = sqlite3.connect(r'C:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\viabilidades.db')
c = conn.cursor()
c.execute("SELECT id, phase_id, taxa_juros_vendas, taxa_correcao_projetada, condicoes_pagamento_json, sistema_amortizacao FROM viability_revenues WHERE phase_id = 5")
rows = c.fetchall()
for row in rows:
    print(f"ID: {row[0]}, Phase ID: {row[1]}")
    print(f"  Juros: {row[2]}, Correcao: {row[3]}, Sistema: {row[5]}")
    if row[4]:
        try:
            conds = json.loads(row[4])
            print(f"  Condicoes ({len(conds)}): {str(conds)[:300]}...")
        except:
            print(f"  Condicoes raw: {str(row[4])[:300]}...")
    else:
        print("  Condicoes vazias")
conn.close()
