import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

if phase.expenses:
    print(f"marketing_valor = {phase.expenses.marketing_valor!r}")
    print(f"marketing_tipo  = {getattr(phase.expenses, 'marketing_tipo', 'N/A')!r}")
    print(f"comercial_valor = {phase.expenses.comercial_valor!r}")
    print(f"comercial_tipo  = {getattr(phase.expenses, 'comercial_tipo', 'N/A')!r}")
    print(f"adm_valor       = {phase.expenses.adm_valor!r}")
    print(f"adm_tipo        = {getattr(phase.expenses, 'adm_tipo', 'N/A')!r}")
    print(f"comissao_corretagem_valor = {getattr(phase.expenses, 'comissao_corretagem_valor', 'N/A')!r}")
    print(f"comissao_corretagem_perc  = {getattr(phase.expenses, 'comissao_corretagem_perc', 'N/A')!r}")
