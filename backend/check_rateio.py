from app.db.database import SessionLocal
from app.models.cost_center import CostCenter

db = SessionLocal()

for cc_id in ["14304", "14305"]:
    cc = db.query(CostCenter).filter(CostCenter.id_sienge == cc_id).first()
    if cc:
        print(f"\n--- {cc.nome} ({cc_id}) ---")
        if cc.apportionment_rules:
            for rule in cc.apportionment_rules:
                print(rule)
        else:
            print("No rules")

db.close()
