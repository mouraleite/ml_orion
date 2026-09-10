import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from app.api.routes.tracking import get_tracking_details

db = SessionLocal()
res = get_tracking_details('c-206', db)
vv = res.get('velocidade_vendas', [])

print("=== Velocidade de Vendas ===")
for row in vv:
    print(f"Ano: {row['ano']}, Vendas: {row['vendas']}, Distratos: {row['distratos']}, Saldo: {row['saldo']}, Perc: {round(row['perc'],2)}, Vel: {round(row['vel'],2)}")

print()
print("Total Units:", res.get('total_units'))
print("Total Sold:", res.get('total_sold'))
print("Total Returned:", res.get('total_returned'))
print("Total Balance:", res.get('total_balance'))
