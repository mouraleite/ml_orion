import sys
from app.main import app
from app.db.database import SessionLocal
from app.services.math_engine import calculate_viability_results

db = SessionLocal()
res = calculate_viability_results(db, 6)
cf = res["monthly_cashflow"]

# Dados do Excel extraídos dos prints
excel_saldo = {
    1: -800000, 2: -941106, 3: -1087543, 4: -1230713, 5: -1372059,
    6: -1516281, 7: -1657427, 8: -1807350, 9: -1978372, 10: -2138805,
    11: -2300148, 12: -2326751, 13: -2367938, 14: -2381796, 15: -2388607,
    16: -2393995, 17: -2402691,
    18: -2407491, 19: -2412491, 20: -2413211, 21: -2434292,
    22: -2440705, 23: -2584065, 24: -2636742,
    25: -2311290, 26: -2318052, 27: -2276356, 28: -2217391, 29: -2157919,
    30: -1984471, 31: -2121746,
    33: -2568041, 34: -2866444, 35: -2929145, 36: -3578450,
    37: -3750344, 38: -3960333, 39: -3944617, 40: -4130999,
    41: -4483343, 42: -4905395, 43: -5186640, 44: -6032671,
    45: -6189802, 46: -6491634
}

excel_entradas = {
    25: 441411, 26: 94133, 27: 93825, 28: 98219, 29: 102613,
    30: 107008, 31: 111402, 32: 115796
}

print(f"{'Mes':>4} {'ERP_Acum':>14} {'Excel_Acum':>14} {'Diferenca':>12}")
print("-" * 50)
for row in cf[:50]:
    mes = row.get("Mes", "?")
    erp_acum = row.get("Caixa_Acumulado", 0) or 0
    exc_acum = excel_saldo.get(mes, None)
    if exc_acum is not None:
        diff = erp_acum - exc_acum
        print(f"{mes:>4} {erp_acum:>14,.0f} {exc_acum:>14,.0f} {diff:>+12,.0f}")
