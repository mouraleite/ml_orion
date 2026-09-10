import sys
from app.db.database import SessionLocal
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase_details import PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates
from app.models.viability import Viability
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
cf = res["monthly_cashflow"]
rec_vendas = 0
rec_juros = 0
custos_obras = 0
custos_terreno = 0
custos_outros = 0
impostos = 0

for r in cf:
    if r["Mes"] <= 46:
        rec_vendas += r.get("Receitas_Vendas", 0)
        rec_juros += r.get("Receitas_Juros", 0)
        custos_obras += r.get("Obras", 0)
        custos_terreno += r.get("Terreno", 0)
        custos_outros += r.get("Projetos", 0) + r.get("Despesas", 0)
        impostos += r.get("Impostos", 0)

print(f"--- Valores Acumulados no Sistema ate o Mes 46 ---")
print(f"Receitas Vendas: {rec_vendas:.2f}")
print(f"Receitas Juros : {rec_juros:.2f}")
print(f"Obras          : {custos_obras:.2f}")
print(f"Terreno        : {custos_terreno:.2f}")
print(f"Outros (Desp)  : {custos_outros:.2f}")
print(f"Impostos       : {impostos:.2f}")
print(f"Exposicao M46  : {(rec_vendas + rec_juros) - (custos_obras + custos_terreno + custos_outros + impostos):.2f}")
