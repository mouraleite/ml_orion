import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(cost_centers)")
for row in cur.fetchall():
    print(row)
