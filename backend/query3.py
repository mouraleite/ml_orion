import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM actual_transactions;')
print(cursor.fetchall())
conn.close()
