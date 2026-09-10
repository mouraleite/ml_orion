import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT id, nome, tipo, classificacao FROM standard_curves')
for row in cursor.fetchall():
    print(row)
