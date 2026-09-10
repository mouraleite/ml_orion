import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT substr(transaction_date, 1, 4), count(*) FROM actual_transactions WHERE is_forecast=0 AND substr(transaction_date, 1, 4) >= '2026' GROUP BY 1")
for row in cur.fetchall():
    print(row)
