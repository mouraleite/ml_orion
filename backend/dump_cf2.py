import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)

cf = res["monthly_cashflow"]
print(f"{'Mes':>4} {'Receitas':>14} {'Despesas':>14} {'Saldo':>14} {'Acumulado':>14}")
print("-" * 65)
acumulado = 0.0
for row in cf[:60]:
    mes = row.get("Mes", row.get("mes", "?"))
    rec = row.get("Receitas", 0) or 0
    # soma todas as colunas que são despesas
    desp_keys = [k for k in row if k not in ("Mes", "mes", "Receitas", "Acumulado", "acumulado")]
    desp_val = sum(row.get(k, 0) or 0 for k in desp_keys)
    saldo = rec - desp_val
    acumulado += saldo
    print(f"{mes:>4} {rec:>14,.0f} {desp_val:>14,.0f} {saldo:>14,.0f} {acumulado:>14,.0f}")

print()
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])
print("Keys mes 46:", list(cf[45].keys()))
