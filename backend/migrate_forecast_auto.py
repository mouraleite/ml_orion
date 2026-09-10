import sqlite3

try:
    conn = sqlite3.connect('viabilidades.db')
    cursor = conn.cursor()
    cursor.execute('ALTER TABLE forecast_itens ADD COLUMN is_auto_generated BOOLEAN DEFAULT 0')
    conn.commit()
    print("Coluna is_auto_generated adicionada com sucesso.")
except Exception as e:
    print(f"Erro (talvez já exista): {e}")
finally:
    conn.close()
