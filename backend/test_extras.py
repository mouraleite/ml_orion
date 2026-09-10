import sqlite3

conn = sqlite3.connect('instance/erp.db')
cursor = conn.cursor()

# Busca quais itens somaram na categoria DESPESAS NAO OPERACIONAIS / EXTRAS
query = """
SELECT a.category, sum(a.value), n.descricao
FROM actual_transactions a
JOIN financial_plans f ON f.name = a.category
JOIN financial_plan_vision_links l ON f.id = l.financial_plan_id
JOIN vision_nodes n ON l.vision_node_id = n.id
JOIN visions v ON n.vision_id = v.id
WHERE a.cost_center_id = 206 
  AND a.is_forecast = 0
  AND v.is_padrao = 1
  AND (n.descricao LIKE '%DESPESAS NAO OPERACIONAIS%' OR n.descricao LIKE '%DESPESAS EXTRAS%')
GROUP BY a.category, n.descricao
"""

cursor.execute(query)
results = cursor.fetchall()

if not results:
    # Tenta fallback if mapping isn't via vision
    query_fb = """
    SELECT category, sum(value)
    FROM actual_transactions
    WHERE cost_center_id = 206 AND is_forecast = 0
    GROUP BY category
    """
    cursor.execute(query_fb)
    for r in cursor.fetchall():
        if "despesa" in r[0].lower() or "extra" in r[0].lower():
            print("Fallback match:", r)
else:
    for r in results:
        print(f"Category: {r[0]} | Sum: {r[1]} | Mapped Node: {r[2]}")

conn.close()
