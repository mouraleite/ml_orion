import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)

cf = res["monthly_cashflow"]
print(f"{'Mes':>4} {'Rec_Vendas':>14} {'Rec_Juros':>12} {'Rec_Total':>12} {'Obras':>12} {'Despesas':>12} {'Impostos':>12} {'FC_Mes':>12} {'FC_Acum':>14}")
print("-" * 110)
for row in cf[:60]:
    mes = row.get("Mes", "?")
    rec_v = row.get("Receitas_Vendas", 0) or 0
    rec_j = row.get("Receitas_Juros", 0) or 0
    rec = row.get("Receitas", 0) or 0
    obra = row.get("Obras", 0) or 0
    desp = row.get("Despesas", 0) or 0
    imp = row.get("Impostos", 0) or 0
    terreno = row.get("Terreno", 0) or 0
    fc_mes = row.get("Fluxo_de_Caixa", 0) or 0
    fc_acum = row.get("Caixa_Acumulado", 0) or 0
    print(f"{mes:>4} {rec_v:>14,.0f} {rec_j:>12,.0f} {rec:>12,.0f} {obra+terreno:>12,.0f} {desp:>12,.0f} {imp:>12,.0f} {fc_mes:>12,.0f} {fc_acum:>14,.0f}")
