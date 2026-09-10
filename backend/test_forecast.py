import sys
import os

# Adjust path to find 'app' module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.forecast import Forecast

db = SessionLocal()

# Search for the forecast manually
ano = 2026
tipo = "DESPESAS"
identifier = "Forecast - 7+5"

fcs = db.query(Forecast).filter(Forecast.ano == ano, Forecast.descricao == identifier, Forecast.tipo == tipo).all()
print(f"Encontrou {len(fcs)} Forecasts para {identifier}")

for f in fcs:
    print(f"ID: {f.id}, Dept: {f.departamento_id}, ItensDespesa: {len(f.itens_despesa)}")

fcs2 = db.query(Forecast).filter(Forecast.descricao == identifier).all()
print(f"Sem filtro de ano/tipo, encontrou {len(fcs2)} Forecasts para {identifier}")
for f in fcs2:
    print(f"ID: {f.id}, Ano: {f.ano}, Tipo: {f.tipo}, Dept: {f.departamento_id}")
