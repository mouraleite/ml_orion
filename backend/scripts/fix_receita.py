import sqlite3
import os
db_path = os.path.join(os.path.dirname(__file__), "..", "viabilidades.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("UPDATE standard_curves SET classificacao = 'Receita' WHERE tipo = 'vendas'")
conn.commit()
conn.close()
