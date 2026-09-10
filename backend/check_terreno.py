import sys
from app.main import app
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()

print("=== TERRENO / EXCHANGES ===")
if phase.exchanges:
    mod = phase.exchanges.modalidade or "N/A"
    print(f"Modalidade: {mod}")
    print(f"Valor Terreno Fixo: {phase.exchanges.valor_terreno_fixo}")
    print(f"Perc Permuta Financeira: {phase.exchanges.perc_permuta_financeira}")
    print(f"Perc Parceria Terrenista: {phase.exchanges.perc_parceria_terrenista}")
    print(f"Permuta Fisica Unidades: {phase.exchanges.permuta_fisica_unidades}")
    print(f"Permuta Fisica Valor Unidade: {phase.exchanges.permuta_fisica_valor_unidade}")
    rateios = getattr(phase.exchanges, 'rateios_config_json', {}) or {}
    print(f"Rateios: {rateios}")
    vincular = rateios.get('vincular_permuta_parceria', True)
    print(f"Vincular permuta: {vincular}")

print()
res = calculate_viability_results(db, 6)
cf = res["monthly_cashflow"]

# Show Terreno column for first few months
print("Mes | Terreno | Obras | Receitas")
for row in cf[:5]:
    mes = row.get("Mes", "?")
    terreno = row.get("Terreno", 0) or 0
    obras = row.get("Obras", 0) or 0
    rec = row.get("Receitas", 0) or 0
    print(f"  {mes} | {terreno:>12,.0f} | {obras:>10,.0f} | {rec:>10,.0f}")

# Total Terreno
total_terreno = sum((row.get("Terreno", 0) or 0) for row in cf)
print(f"\nTotal Terreno no FC: R$ {total_terreno:,.0f}")

# VGV calc
vgv_bruto = phase.revenue.vgv_total
comissao = vgv_bruto * 0.05
vgv_liq = vgv_bruto - comissao
perc_perm = phase.exchanges.perc_parceria_terrenista if phase.exchanges else 0
permuta = vgv_liq * (perc_perm / 100)
print(f"VGV Bruto: R$ {vgv_bruto:,.0f}")
print(f"VGV Liq: R$ {vgv_liq:,.0f}")
print(f"25% Permuta esperada: R$ {permuta:,.0f}")
