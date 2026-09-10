from app.db.database import SessionLocal
from app.models.payment_plan import PaymentPlan

db = SessionLocal()
plans = db.query(PaymentPlan).all()
print("Payment Plans:")
for p in plans:
    print(p.id, p.nome)
db.close()
