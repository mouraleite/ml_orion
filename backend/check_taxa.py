import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import _get_taxa_juros, _get_taxa_inflacao

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase and phase.revenue:
    print(f'Taxa Juros Vendas (a.a.): {phase.revenue.taxa_juros_vendas}')
    print(f'Sistema Amortizacao: {phase.revenue.sistema_amortizacao}')
    print()
    print('Condições (condicoes_pagamento_json):')
    for c in phase.revenue.condicoes_pagamento_json:
        print(f"  {c}")
