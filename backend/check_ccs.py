from app.db.database import SessionLocal
from app.models.cost_center import CostCenter

db = SessionLocal()

print("Searching for MLDU or ELLENCO or 143...")
ccs = db.query(CostCenter).all()
for cc in ccs:
    nome = cc.nome.upper() if cc.nome else ""
    if "MLDU" in nome or "ELL" in nome or "143" in (cc.id_sienge or "") or "143" in nome:
        print(f"ID: {cc.id} | Sienge: {cc.id_sienge} | Nome: {cc.nome}")

db.close()
