import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT db_id, name, tp_conta FROM planos_financeiros WHERE tp_conta="R" LIMIT 10;')
print(cursor.fetchall())
conn.close()
