import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase and phase.revenue:
    print(f'Velocidade Vendas JSON: {phase.revenue.velocidade_vendas_json}')
