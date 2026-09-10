import pandas as pd
import shutil
import tempfile
import os

try:
    path = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Orçamento - Vendas\Orcamento de vendas.xlsx"
    temp_path = os.path.join(tempfile.gettempdir(), "copy_orcamento.xlsx")
    shutil.copy2(path, temp_path)
    
    df = pd.read_excel(temp_path, sheet_name="Orcamento", header=1)
    
    df_2026 = df[df['Ano'] == 2026]
    print("\n=== VALORES ÚNICOS DE 'Versao orcamento' ===")
    print(df_2026['Versao orcamento'].unique())
    print("\n=== VALORES ÚNICOS DE 'Tipo de Venda' ===")
    print(df_2026['Tipo de Venda'].unique())
    print("\n=== VALORES ÚNICOS DE 'Origem Venda' ===")
    print(df_2026['Origem Venda'].unique())

except Exception as e:
    print(f"Error reading file: {e}")
