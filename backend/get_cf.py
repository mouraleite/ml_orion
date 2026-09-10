from app.db.database import SessionLocal
import app.models.phase
import app.models.viability
import app.models.revenue
import app.models.expenses
import app.models.construction
import app.models.funding
import app.models.taxes
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results
import warnings
warnings.filterwarnings('ignore')

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase:
    res = calculate_viability_results(db, phase)
    cf = res['monthly_cashflow']
    for m in range(40, 50):
        if m < len(cf):
            row = cf[m]
            saidas = row['Obras'] + row['Despesas'] + row['Impostos']
            mov = row['Fluxo_de_Caixa']
            acum = row['Caixa_Acumulado']
            print(f"Mes {m+1}: Entradas={row['Receitas']:.0f}, Saidas={saidas:.0f}, Mov={mov:.0f}, Acum={acum:.0f}")
    
    exposicao = min([r['Caixa_Acumulado'] for r in cf])
    idx = [r['Caixa_Acumulado'] for r in cf].index(exposicao) + 1
    print(f"Exposicao Maxima: {exposicao:.0f} no Mes {idx}")
