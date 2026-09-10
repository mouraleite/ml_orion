import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT id, id_sienge, nome FROM cost_centers WHERE id_sienge LIKE '141%'")
print("CCs for cg-141:")
for row in cur.fetchall():
    print(row)
