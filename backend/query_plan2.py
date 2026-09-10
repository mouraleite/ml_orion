import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT db_id, name, tp_conta FROM planos_financeiros WHERE db_id LIKE "1%" AND tp_conta="R" LIMIT 10;')
print("1%:", cursor.fetchall())
cursor.execute('SELECT db_id, name, tp_conta FROM planos_financeiros WHERE db_id LIKE "2%" AND tp_conta="R" LIMIT 10;')
print("2%:", cursor.fetchall())
conn.close()
