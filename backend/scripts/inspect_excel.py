import pandas as pd
import os
import glob

FORECAST_BASE_DIR = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Sienge - 2653 - Comparativo Orçamento Empresarial X Realizado Agrupado - Forecast\2026"
folder = os.path.join(FORECAST_BASE_DIR, "Forecast - 7+5")
files = glob.glob(os.path.join(folder, "**", "*.xlsx"), recursive=True)

for f in files:
    if "~$" in f: continue
    print(f"Lendo: {f}")
    df = pd.read_excel(f, header=None)
    
    current_cc = None
    for idx in range(len(df)):
        row = df.iloc[idx].values
        
        # Identify Cost Center
        for val in row:
            if str(val).strip().lower() == "centro de custo":
                for j in range(len(row)):
                    if pd.notna(row[j]) and str(row[j]).strip() and "centro de custo" not in str(row[j]).strip().lower():
                        current_cc = str(row[j]).strip()
                        break
                break
                
        # If we are in one of the problematic CCs, print rows
        if current_cc and any(code in current_cc for code in ["70203", "70202", "70201"]):
            tipo = str(row[4]).strip() if pd.notna(row[4]) else ""
            if "Total" in str(row[0]) or "Centro" in str(row[0]):
                pass # skip
            else:
                conta = str(row[0]).strip()
                if conta != "nan":
                    print(f"[{current_cc}] Tipo: '{tipo}' | Conta: {conta} - {str(row[1]).strip()[:30]}")

