import pandas as pd
import os
import glob

FORECAST_BASE_DIR = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Sienge - 2653 - Comparativo Orçamento Empresarial X Realizado Agrupado - Forecast\2026"
folder = os.path.join(FORECAST_BASE_DIR, "Forecast - 7+5")
files = glob.glob(os.path.join(folder, "**", "*.xlsx"), recursive=True)

for f in files:
    if "~$" in f: continue
    df = pd.read_excel(f, header=None)
    
    current_cc = None
    meses_cols = {}
    
    for idx in range(len(df)):
        row = df.iloc[idx].values
        
        # Identify Cost Center
        found_cc = False
        for i, val in enumerate(row):
            if str(val).strip().lower() == "centro de custo":
                for j in range(i+1, len(row)):
                    if pd.notna(row[j]) and str(row[j]).strip() and "centro de custo" not in str(row[j]).strip().lower():
                        current_cc = str(row[j]).strip()
                        found_cc = True
                        break
                break
                
        if found_cc: continue
                
        # Identify Meses
        if current_cc and "70201" in current_cc:
            # find meses
            for i, val in enumerate(row):
                if pd.notna(val) and "/" in str(val).strip():
                    if "orçado" in str(df.iloc[idx+1, i]).strip().lower() or "orçado" in str(df.iloc[idx+1, min(i+1, len(row)-1)]).strip().lower() or "orçado" in str(df.iloc[idx+1, max(i-1, 0)]).strip().lower():
                        # Just grab the index for simplicity
                        pass
                        
            tipo = str(row[4]).strip() if pd.notna(row[4]) else ""
            if tipo == "R":
                print(f"File: {os.path.basename(os.path.dirname(f))} | CC: {current_cc} | Conta: {row[0]}")
                # Print some columns
                vals = [x for x in row[5:] if pd.notna(x) and isinstance(x, (int, float))]
                print(f"Vals: {sum(vals)}")
