import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)

cf = res["monthly_cashflow"]
print(f"{'Mes':>4} {'Receitas':>14} {'Obras':>12} {'Despesas':>12} {'Impostos':>12} {'Funding':>12} {'FC_Mes':>12} {'FC_Acum':>14}")
print("-" * 95)
for row in cf[:55]:
    mes = row.get("Mes", "?")
    rec = row.get("Receitas", 0) or 0
    obra = row.get("Obras", 0) or 0
    desp = row.get("Despesas", 0) or 0
    imp = row.get("Impostos", 0) or 0
    fund_e = row.get("Funding_Entrada", 0) or 0
    fund_d = row.get("Funding_Despesas", 0) or 0
    terreno = row.get("Terreno", 0) or 0
    fc_mes = row.get("Fluxo_de_Caixa", 0) or 0
    fc_acum = row.get("Caixa_Acumulado", 0) or 0
    print(f"{mes:>4} {rec:>14,.0f} {obra:>12,.0f} {desp:>12,.0f} {imp:>12,.0f} {fund_e+fund_d:>12,.0f} {fc_mes:>12,.0f} {fc_acum:>14,.0f}")

print()
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])
