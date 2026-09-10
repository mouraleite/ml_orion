from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
ind_global = res.get('indicators', {})
ind_emp = res.get('indicators_empreendedor', {})
print(f"GLOBAL Exposicao: {ind_global.get('exposicao_maxima')}")
print(f"GLOBAL Periodo: {ind_global.get('periodo_exposicao')}")
print(f"EMPREENDEDOR Exposicao: {ind_emp.get('exposicao_maxima')}")
print(f"EMPREENDEDOR Periodo: {ind_emp.get('periodo_exposicao')}")
