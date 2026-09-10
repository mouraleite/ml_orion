import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase and phase.revenue:
    taxa_corr = getattr(phase.revenue, "taxa_correcao_projetada", None)
    tipo_corr = getattr(phase.revenue, "tipo_correcao_projetada", None)
    print(f'Taxa Correção Projetada: {taxa_corr}')
    print(f'Tipo Correção: {tipo_corr}')
    print()
    print('Condições completas:')
    for c in phase.revenue.condicoes_pagamento_json:
        nome = c.get("nome", "?")
        perc = c.get("perc", 0)
        inst = c.get("inst", 0)
        aplica_j = c.get("aplica_juros", True)
        aplica_c = c.get("aplica_correcao", True)
        perc_ent = c.get("perc_entrada", 0)
        print(f"  {nome}: {perc}% | {inst}x | juros={aplica_j} | correcao={aplica_c} | entrada={perc_ent}%")
