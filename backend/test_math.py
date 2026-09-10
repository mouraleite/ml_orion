import sys
sys.path.append('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
from app.db.session import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
phase = db.query(Phase).first()
if phase:
    res = calculate_viability_results(db, phase.id)
    print("Phase config injected?", "phase" in res)
    print(res.get("phase", {}))
else:
    print("No phase found")
