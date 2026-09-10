import asyncio
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.viability import Viability
from app.services.math_engine import calculate_viability_results

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

v = db.query(Viability).order_by(Viability.id.desc()).first()
if v:
    res = calculate_viability_results(v.phases[0].id if v.phases else v.id, db)
    ind = res['indicators']
    print(f"Exposicao Maxima: {ind['exposicao_maxima']}")
    
    # Check if Obras is concentrated
    cf = res['monthly_cashflow']
    obras_sum_12 = sum([m['Obras'] for m in cf[:12]])
    obras_total = sum([m['Obras'] for m in cf])
    print(f"Obras first 12 months: {obras_sum_12}")
    print(f"Obras total: {obras_total}")
    
    for i in range(12):
        print(f"M{i+1}: Rec={cf[i]['Receitas']:.0f}, Obr={cf[i]['Obras']:.0f}, Desp={cf[i]['Despesas']:.0f}, CX={cf[i]['Fluxo_de_Caixa']:.0f}, Acum={cf[i]['Caixa_Acumulado']:.0f}")
else:
    print('No viability found')
