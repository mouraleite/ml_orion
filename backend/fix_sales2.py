import sqlite3

conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()

cursor.execute("UPDATE actual_transactions SET value = -value, category = 'VGV Vendido' WHERE transaction_type = 'SALE' AND value < 0;")
conn.commit()

cursor.execute("SELECT transaction_type, count(*), sum(value) FROM actual_transactions GROUP BY transaction_type;")
print(cursor.fetchall())
conn.close()
