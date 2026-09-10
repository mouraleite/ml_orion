import sys, pandas as pd
sys.path.append('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
file_path = 'C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/V10_RES CEN PARQUE II.xlsb'
df = pd.read_excel(file_path, sheet_name=0, engine='pyxlsb')
print('columns:', df.columns[:5])
for i in range(10):
    print(df.iloc[i].values[:5])
