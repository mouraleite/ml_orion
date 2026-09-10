import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT id, descricao, tipo, ano FROM orcamentos WHERE tipo="RECEITAS";')
print(cursor.fetchall())
conn.close()
