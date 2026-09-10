import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT id, departamento_id, tipo FROM orcamentos WHERE ano=2026 AND tipo="DESPESAS";')
print(cursor.fetchall())
conn.close()
