import sqlite3
conn = sqlite3.connect('viabilidades.db')
conn.execute("UPDATE orcamentos SET departamento_id = NULL WHERE descricao = 'Carga Inicial Sienge 2026'")
conn.commit()
conn.close()
