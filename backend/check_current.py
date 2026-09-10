import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
res = calculate_viability_results(db, 6)

print("Receitas Mes 46:", res["monthly_cashflow"][45]["Receitas"])
print("Despesas Mes 46:", res["monthly_cashflow"][45]["Despesas_Totais"])
print("Acumulado Mes 46:", res["monthly_cashflow"][45]["Acumulado"])
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])
