import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
cf = res["monthly_cashflow"]

# Dados mensais do Excel (do print 2)
excel_entradas = {
    25: 441411, 26: 94133, 27: 93825, 28: 98219, 29: 102613,
    30: 107008, 31: 111402, 32: 115796
}
excel_saidas = {
    25: 115598, 26: 100895, 27: 52128, 28: 39254, 29: 43141,
    30: 27851, 31: 127275,
}

print(f"{'Mes':>4} {'ERP_Rec':>12} {'Exc_Rec':>12} {'Dif_Rec':>10} | {'ERP_Obr':>10} {'ERP_Desp':>10} {'ERP_Imp':>9} | {'Exc_Sai':>10}")
print("-" * 100)
for row in cf[23:35]:
    mes = row.get("Mes", "?")
    erp_rec = row.get("Receitas", 0) or 0
    erp_rv = row.get("Receitas_Vendas", 0) or 0
    erp_rj = row.get("Receitas_Juros", 0) or 0
    erp_obr = row.get("Obras", 0) or 0
    erp_desp = row.get("Despesas", 0) or 0
    erp_imp = row.get("Impostos", 0) or 0
    exc_rec = excel_entradas.get(mes, None)
    exc_sai = excel_saidas.get(mes, None)
    if exc_rec is not None:
        dif_rec = erp_rec - exc_rec
        print(f"{mes:>4} {erp_rec:>12,.0f} {exc_rec:>12,.0f} {dif_rec:>+10,.0f} | {erp_obr:>10,.0f} {erp_desp:>10,.0f} {erp_imp:>9,.0f} | {exc_sai:>10}")
    else:
        print(f"{mes:>4} {erp_rec:>12,.0f}            N/A           N/A | {erp_obr:>10,.0f} {erp_desp:>10,.0f} {erp_imp:>9,.0f} |        N/A")

print()
print("Detalhamento do mes 25 e 26:")
for row in cf[23:27]:
    mes = row.get("Mes", "?")
    print(f"Mes {mes}: Rec_Vendas={row.get('Receitas_Vendas',0):,.0f} | Rec_Juros={row.get('Receitas_Juros',0):,.0f} | Total_Rec={row.get('Receitas',0):,.0f}")
