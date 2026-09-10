import sqlite3
conn = sqlite3.connect('viabilidades.db')
cur = conn.cursor()
cur.execute("SELECT id, company_id, name FROM cost_centers WHERE id=203")
print("CC 203:", cur.fetchone())

cur.execute("SELECT id, company_id, name FROM cost_centers WHERE company_id=141")
print("CCs for company 141:")
for row in cur.fetchall():
    print(row)
