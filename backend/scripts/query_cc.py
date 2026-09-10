import sqlite3

conn = sqlite3.connect('viabilidades.db')
c = conn.cursor()

c.execute("SELECT id_sienge, nome FROM cost_centers WHERE nome LIKE '%11300%'")
ccs = c.fetchall()

print("Cost centers com 11300:")
for r in ccs:
    print(r)
