import sqlite3
import os
db_path = r'C:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\ml_orion.db'
if not os.path.exists(db_path):
    print("Database file doesn't exist!")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("Tables in database:")
    for t in tables:
        print(t[0])
    conn.close()
