import sys
import os
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
print("VGV no Indicadores:", res["indicators"]["vgv_total"])
print("Receitas Mes 46:", res["monthly_cashflow"][45]["Receitas"])
