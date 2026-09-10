import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
import json

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

print("=== REVENUE MODEL ===")
print(f"VGV Total no banco: {phase.revenue.vgv_total}")
print(f"Taxa Juros Vendas: {phase.revenue.taxa_juros_vendas}")
print(f"Sistema Amortização: {phase.revenue.sistema_amortizacao}")
print(f"Comissão Vendas: {getattr(phase.expenses, 'comissao_vendas', 'N/A')}")
print(f"Comissão Corretagem Valor: {getattr(phase.expenses, 'comissao_corretagem_valor', 'N/A')}")
print(f"Comissão Corretagem %: {getattr(phase.expenses, 'comissao_corretagem_perc', 'N/A')}")
print()
print("=== CONDICOES COMPLETAS (raw) ===")
conds = phase.revenue.condicoes_pagamento_json
if isinstance(conds, list):
    print(f"Número de condições: {len(conds)}")
    for i, c in enumerate(conds):
        print(f"[{i}] {json.dumps(c, ensure_ascii=False)}")
else:
    print(f"Tipo inesperado: {type(conds)}")
    print(conds)
