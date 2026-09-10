import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

vgv_total_base = phase.revenue.vgv_total if phase.revenue and phase.revenue.vgv_total else 0.0
vgv_total = vgv_total_base * 1.0  # sem cenario
print(f"VGV Total no ponto de calculo de MKT: R$ {vgv_total:,.2f}")

val_mkt = phase.expenses.marketing_valor or 0.0
marketing_tipo = getattr(phase.expenses, 'marketing_tipo', '%')
print(f"marketing_valor={val_mkt}, marketing_tipo={marketing_tipo!r}")

marketing = val_mkt if marketing_tipo == 'R$' else vgv_total * (val_mkt / 100)
print(f"Marketing calculado: R$ {marketing:,.2f}")
print(f"3% de {vgv_total:,.2f} = R$ {vgv_total * 0.03:,.2f}")

# Agora calcular como o motor faz
val_comissao = getattr(phase.expenses, 'comissao_corretagem_valor', 0.0) or 0.0
comissao = vgv_total * (val_comissao / 100)
vgv_bruto = vgv_total
vgv_total_liq = vgv_bruto - comissao
print(f"VGV Bruto: R$ {vgv_bruto:,.2f}")
print(f"Comissao ({val_comissao}%): R$ {comissao:,.2f}")
print(f"VGV Liquido: R$ {vgv_total_liq:,.2f}")
print(f"3% do VGV Liquido: R$ {vgv_total_liq * 0.03:,.2f}")
