import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "viabilidades.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE standard_curves ADD COLUMN classificacao VARCHAR DEFAULT 'Custo'")
    print("Coluna 'classificacao' adicionada com sucesso.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Coluna 'classificacao' já existe.")
    else:
        print(f"Erro ao adicionar coluna: {e}")

cursor.execute("UPDATE standard_curves SET classificacao = 'Despesa' WHERE tipo IN ('vendas', 'marketing')")
cursor.execute("UPDATE standard_curves SET classificacao = 'Custo' WHERE tipo NOT IN ('vendas', 'marketing')")

conn.commit()
conn.close()
