import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT category, sum(value) FROM actual_transactions WHERE cost_center_id=(SELECT id FROM cost_centers WHERE id_sienge='14100') AND transaction_type='OUTCOME' AND is_forecast=1 AND substr(transaction_date, 1, 4)='2027' GROUP BY category")
for row in cur.fetchall():
    print(row)
