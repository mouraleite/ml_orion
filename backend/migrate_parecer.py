import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'viabilidades.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE viabilities ADD COLUMN parecer_executivo TEXT")
    print("Coluna parecer_executivo adicionada com sucesso na tabela viabilities.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Coluna parecer_executivo já existe na tabela viabilities.")
    else:
        print(f"Erro ao adicionar coluna: {e}")

conn.commit()
conn.close()
