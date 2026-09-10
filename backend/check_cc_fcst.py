import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT cost_center_id, sum(value) FROM actual_transactions WHERE is_forecast=1 GROUP BY 1")
for row in cur.fetchall():
    print("CC with forecast:", row)
