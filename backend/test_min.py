import sys
from app.db.database import SessionLocal
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase_details import PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates
from app.models.viability import Viability
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results
import numpy_financial as npf

db = SessionLocal()
res = calculate_viability_results(db, 6)
cf = res["monthly_cashflow"]
min_cum = 0
min_month = 0
arr = []
for row in cf:
    arr.append(row.get("Fluxo_de_Caixa", 0))
    if row.get("Caixa_Acumulado", 0) < min_cum:
        min_cum = row.get("Caixa_Acumulado", 0)
        min_month = row.get("Mes")

tir_mensal = npf.irr(arr)
tir_aa = ((1 + tir_mensal) ** 12 - 1) * 100

print(f"Exposicao Max: {min_cum:.2f} no Mes {min_month}")
print(f"TIR Anual do DB: {tir_aa:.2f}%")
print(f"Payback: {res['indicators'].get('payback')}")
