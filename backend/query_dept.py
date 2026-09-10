import sqlite3
conn = sqlite3.connect('viabilidades.db')
cursor = conn.cursor()
cursor.execute('SELECT dp.departamento_id, pf.db_id, pf.name FROM departamento_planos dp JOIN planos_financeiros pf ON dp.plano_financeiro_id = pf.id WHERE dp.permitido=1;')
print(cursor.fetchall())
conn.close()
