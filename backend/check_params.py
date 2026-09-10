import os
import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase and phase.viability:
    print(f"Taxa Juros: {phase.viability.taxa_juros}")
    print(f"Taxa Inflacao: {phase.viability.taxa_inflacao}")
else:
    print("Phase or Viability not found")
