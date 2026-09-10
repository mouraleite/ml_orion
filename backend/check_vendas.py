import sys
import json
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase and phase.revenue:
    print("Vendas JSON:", phase.revenue.velocidade_vendas_json)
    print("Condicoes:")
    for cond in phase.revenue.condicoes_pagamento_json:
        if "curve_json" in cond:
            print("Cond:", cond["nome"], "has curve")
        else:
            print("Cond:", cond["nome"], "no curve")
