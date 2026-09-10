import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.session import SessionLocal
from app.models.vision import Vision, FinancialPlanVisionLink
from app.models.financial_plan import FinancialPlan

db = SessionLocal()
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

import json
print("DRE KEYS:")
print(json.dumps(list(set(cached_cat_to_group.values())), indent=2))
