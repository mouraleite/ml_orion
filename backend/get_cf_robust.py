import os
import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results
import warnings
warnings.filterwarnings('ignore')

db = SessionLocal()
res = calculate_viability_results(db, 6)
cf = res['monthly_cashflow']
for m in range(40, 50):
    if m < len(cf):
        row = cf[m]
        saidas = row['Obras'] + row['Despesas'] + row['Impostos']
        mov = row['Fluxo_de_Caixa']
        acum = row['Caixa_Acumulado']
        print(f"Mes {m+1}: Vendas={row['Receitas_Vendas']:.0f}, Juros={row['Receitas_Juros']:.0f}, Total_Rec={row['Receitas']:.0f}")

exposicao = min([r['Caixa_Acumulado'] for r in cf]) if cf else 0
idx = [r['Caixa_Acumulado'] for r in cf].index(exposicao) + 1 if cf else 0
print(f"Exposicao Maxima: {exposicao:.0f} no Mes {idx}")
