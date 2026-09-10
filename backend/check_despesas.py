import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

if phase.expenses:
    mkt_tipo = getattr(phase.expenses, 'marketing_tipo', '%')
    mkt_valor = phase.expenses.marketing_valor or 0.0
    com_tipo = getattr(phase.expenses, 'comercial_tipo', '%')
    com_valor = phase.expenses.comercial_valor or 0.0
    adm_tipo = getattr(phase.expenses, 'adm_tipo', '%')
    adm_valor = phase.expenses.adm_valor or 0.0
    comissao_valor = getattr(phase.expenses, 'comissao_corretagem_valor', 0.0) or 0.0

    vgv_bruto = phase.revenue.vgv_total if phase.revenue else 0
    vgv_liq = vgv_bruto * (1 - comissao_valor/100)

    mkt_real = mkt_valor if mkt_tipo == 'R$' else vgv_liq * (mkt_valor / 100)
    com_real = com_valor if com_tipo == 'R$' else vgv_liq * (com_valor / 100)
    adm_real = adm_valor if adm_tipo == 'R$' else vgv_liq * (adm_valor / 100)

    print(f"Marketing: {mkt_valor} {mkt_tipo} = R$ {mkt_real:,.0f}")
    print(f"Comercial: {com_valor} {com_tipo} = R$ {com_real:,.0f}")
    print(f"ADM: {adm_valor} {adm_tipo} = R$ {adm_real:,.0f}")
    print(f"Comissao Corretagem: {comissao_valor}%")
    print()
    print(f"VGV Bruto: R$ {vgv_bruto:,.0f}")
    print(f"VGV Liquido (usado no FC): R$ {vgv_liq:,.0f}")
    print()
    curva_mkt = getattr(phase.expenses, 'curva_marketing_json', None)
    curva_com = getattr(phase.expenses, 'curva_comercial_json', None)
    print(f"Curva Marketing: {curva_mkt}")
    print(f"Curva Comercial: {curva_com}")
