import sys
sys.path.append('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
from app.db.session import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phases = db.query(Phase).limit(5).all()
for p in phases:
    print(f"Phase {p.id}")
