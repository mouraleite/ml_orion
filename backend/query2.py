import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT orcamento_id, COUNT(*) FROM orcamento_itens GROUP BY orcamento_id;')
print(cursor.fetchall())
conn.close()
