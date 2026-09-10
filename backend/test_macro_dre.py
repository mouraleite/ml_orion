import sys
from app.db.database import SessionLocal
from app.main import app
from app.api.routes.tracking import _calc_actuals_for_cc
from app.models.cost_center import CostCenter

db = SessionLocal()
try:
    print("Checking Macro 143 DRE...")
    ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like("143%")).all()
    
    from app.models.vision import Vision, FinancialPlanVisionLink
    from app.models.financial_plan import FinancialPlan
    cached_cat_to_group = {}
    vision = db.query(Vision).filter_by(is_padrao=True).first()
    if not vision: vision = db.query(Vision).first()
    if vision:
        for node in vision.nodes:
            links = db.query(FinancialPlanVisionLink).filter_by(vision_node_id=node.id).all()
            for link in links:
                fp = db.query(FinancialPlan).filter_by(id=link.financial_plan_id).first()
                if fp:
                    cached_cat_to_group[fp.name.strip().lower()] = node.descricao.strip().upper()

    macro_dre = {}
    for sub_cc in ccs:
        act = _calc_actuals_for_cc(db, sub_cc.id, None, 1.0, 1.0, cached_cat_to_group)
        for row in act.get("dre", []):
            if row.get("is_percentage"): continue
            item = row["item"]
            macro_dre[item] = macro_dre.get(item, 0.0) + row["valor"]
            
    print("Macro 143 DRE:")
    for item, val in macro_dre.items():
        if val > 0 or val < 0:
            print(f"  {item}: {val}")

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
