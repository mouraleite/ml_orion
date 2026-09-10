import sys
import json
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.viability import Viability
from app.models.phase import Phase
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.taxes import PhaseTaxes
from app.services.math_engine import calculate_viability_results

def run():
    db = sessionmaker(bind=engine)()
    v = db.query(Viability).order_by(Viability.id.desc()).first()
    if not v:
        print("No viability found")
        return
    
    phase = v.phases[0]
    res = calculate_viability_results(phase)
    
    print("=== DRE ===")
    for k, v in res["dre"].items():
        print(f"{k}: {v:,.2f}")
    
    print("\n=== INDICATORS ===")
    for k, v in res["indicators"].items():
        if isinstance(v, float):
            print(f"{k}: {v:,.2f}")
        else:
            print(f"{k}: {v}")

run()
