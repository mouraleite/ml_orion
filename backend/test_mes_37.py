import sys
import os
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results
import json

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

old_offset = phase.revenue.vendas_offset
# Change start month to 37
phase.revenue.vendas_offset = 37

# Set the Excel matrix
old_cond = phase.revenue.condicoes_pagamento_json
phase.revenue.condicoes_pagamento_json = [
    {"nome": "A VISTA", "perc": 0.35, "inst": 1, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 100.0, "parcelas_entrada": 1},
    {"nome": "24", "perc": 1.05, "inst": 24, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "36", "perc": 1.05, "inst": 36, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "48", "perc": 0.35, "inst": 48, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "60", "perc": 2.10, "inst": 60, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "120", "perc": 17.48, "inst": 120, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "180", "perc": 77.62, "inst": 180, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1}
]

# Note: Commission is already 5.0 in the DB, so vgv_total is 17.8M
res = calculate_viability_results(db, 6)

print("Receitas Mes 46:", res["monthly_cashflow"][45]["Receitas"])
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])

phase.revenue.vendas_offset = old_offset
phase.revenue.condicoes_pagamento_json = old_cond
