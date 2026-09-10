import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT nome FROM cost_centers WHERE track_in_dashboard=1')
for r in cursor.fetchall():
    print(r[0])
conn.close()
