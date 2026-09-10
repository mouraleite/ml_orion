from app.db.database import SessionLocal
from app.models.viability import Viability
from app.models.phase import Phase
from app.models.revenue import ViabilityRevenue
from app.models.construction import Construction
from app.models.payment_plan import PaymentPlan
from app.models.cost_center import CostCenter
from app.models.exchanges import ViabilityExchanges
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
ind_global = res.get('indicators', {})
ind_emp = res.get('indicators_empreendedor', {})
print(f"GLOBAL Receita Bruta: {sum(x['Receitas_Vendas'] for x in res['monthly_cashflow'])}")
print(f"EMP Receita Bruta: {sum(x['Receitas_Vendas'] for x in res['monthly_cashflow_empreendedor'])}")

for nome, flux in res['monthly_cashflow_parceiros'].items():
    print(f"{nome} Receita Bruta: {sum(x['Receitas_Vendas'] for x in flux)}")
