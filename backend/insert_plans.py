from app.db.database import SessionLocal
from app.models.payment_plan import PaymentPlan

db = SessionLocal()

plan_names = [
    "À vista",
    "24x",
    "36x",
    "48x",
    "60x",
    "120x",
    "180x"
]

for name in plan_names:
    existing = db.query(PaymentPlan).filter(PaymentPlan.nome == name).first()
    if not existing:
        new_plan = PaymentPlan(nome=name)
        db.add(new_plan)
        print(f"Added: {name}")

db.commit()
db.close()
