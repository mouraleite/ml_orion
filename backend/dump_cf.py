import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)

cf = res["monthly_cashflow"]
print(f"{'Mes':>4} {'Receitas':>14} {'Obras':>14} {'Acumulado':>14}")
print("-" * 50)
for row in cf:
    mes = row.get("Mes", row.get("mes", "?"))
    rec = row.get("Receitas", 0) or 0
    # find obras key
    obra_keys = [k for k in row if "obra" in k.lower() or "Obra" in k]
    obra_val = sum(row.get(k, 0) or 0 for k in obra_keys)
    acu = row.get("Acumulado", row.get("acumulado", 0)) or 0
    print(f"{mes:>4} {rec:>14,.0f} {obra_val:>14,.0f} {acu:>14,.0f}")
