import sys
import os
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

old_cond = phase.revenue.condicoes_pagamento_json
old_vgv = phase.revenue.vgv_total if phase.revenue else None

# Force VGV = 17.012.240 (which assumes 14 lots are Permuta and don't generate cash)
phase.revenue.vgv_total = 17012240
# And 0 comissao, because 17M is already liquido
phase.expenses.comissao_corretagem_valor = 0

phase.revenue.condicoes_pagamento_json = [
    {"nome": "120", "perc": 18.38, "inst": 120, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "180", "perc": 81.62, "inst": 180, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1}
]

res = calculate_viability_results(db, 6)

print("Receitas Mes 46:", res["monthly_cashflow"][45]["Receitas"])
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])

phase.revenue.condicoes_pagamento_json = old_cond
if old_vgv is not None:
    phase.revenue.vgv_total = old_vgv
