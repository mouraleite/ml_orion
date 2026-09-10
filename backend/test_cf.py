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
print("Mes ; Vendas ; Juros ; Obras ; Aquisicao ; Projetos ; Impostos ; Despesas ; Fluxo ; Acumulado")
for r in cf:
    if abs(r.get("Fluxo_de_Caixa", 0)) > 0.01:
        v = r.get("Receitas_Vendas",0)
        j = r.get("Receitas_Juros",0)
        o = r.get("Obras",0)
        a = r.get("Terreno",0)
        p = r.get("Projetos",0)
        i = r.get("Impostos",0)
        d = r.get("Despesas",0)
        f = r.get("Fluxo_de_Caixa",0)
        c = r.get("Caixa_Acumulado",0)
        print(f'{r.get("Mes")} ; {v:.0f} ; {j:.0f} ; {o:.0f} ; {a:.0f} ; {p:.0f} ; {i:.0f} ; {d:.0f} ; {f:.0f} ; {c:.0f}')
