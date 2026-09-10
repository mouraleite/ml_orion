import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT apportionment_rules FROM cost_centers WHERE id=206")
print(cur.fetchone())
