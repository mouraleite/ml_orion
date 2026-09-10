import sqlite3
conn = sqlite3.connect('viabilidades.db')
try:
    conn.execute("ALTER TABLE companies ADD COLUMN tipo_empresa TEXT DEFAULT 'SPE'")
    conn.commit()
    print("Coluna tipo_empresa adicionada com sucesso!")
except Exception as e:
    print(f"Erro (pode ser que já exista): {e}")
conn.close()
