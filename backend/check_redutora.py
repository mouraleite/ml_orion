import sqlite3
c = sqlite3.connect('viabilidades.db').cursor()
c.execute("SELECT name, fl_redutora FROM planos_financeiros WHERE name LIKE '%Reten%'")
for row in c.fetchall():
    print(row)
