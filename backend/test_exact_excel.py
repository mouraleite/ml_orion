import sys
import os
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

# Backup
old_cond = phase.revenue.condicoes_pagamento_json
old_vgv = phase.revenue.vgv_total if phase.revenue else None
old_curve = phase.revenue.velocidade_vendas_json if phase.revenue else None
old_offset = phase.revenue.vendas_offset if phase.revenue else None

# VGV = 17.887.844 (calculated by 286 * 62545)
# Set exact Excel distribution (Total 286 lots)
phase.revenue.condicoes_pagamento_json = [
    {"nome": "A VISTA", "perc": 1/286*100, "inst": 1, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 100.0, "parcelas_entrada": 1},
    {"nome": "24", "perc": 3/286*100, "inst": 24, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "36", "perc": 3/286*100, "inst": 36, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "48", "perc": 1/286*100, "inst": 48, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "60", "perc": 6/286*100, "inst": 60, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "120", "perc": 50/286*100, "inst": 120, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1},
    {"nome": "180", "perc": 222/286*100, "inst": 180, "aplica_juros": True, "aplica_correcao": True, "perc_entrada": 6.0, "parcelas_entrada": 1}
]

# Set exact Excel sales curve
excel_curve = [
    # M25, M26, M27...
    114, 11, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
    6, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 6,
    1, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 6,
    3, 3, 3, 3, 3
]
# Convert lots to percentages
total_excel_lots = sum(excel_curve) # Should be 286
perc_curve = [(lots / total_excel_lots) * 100 for lots in excel_curve]

phase.revenue.velocidade_vendas_json = perc_curve
phase.revenue.vendas_offset = 25
phase.revenue.vgv_total = 17887844
phase.expenses.comissao_corretagem_valor = 0.0 # because vgv is already 17.8M

res = calculate_viability_results(db, 6)

print("Receitas Mes 46:", res["monthly_cashflow"][45]["Receitas"])
print("Exposicao Maxima:", res["indicators"]["exposicao_maxima"])

# Restore
phase.revenue.condicoes_pagamento_json = old_cond
if old_vgv is not None: phase.revenue.vgv_total = old_vgv
if old_curve is not None: phase.revenue.velocidade_vendas_json = old_curve
if old_offset is not None: phase.revenue.vendas_offset = old_offset
