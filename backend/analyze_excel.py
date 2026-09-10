import pandas as pd
import warnings
warnings.filterwarnings('ignore')

file_path = '../bases/Taguai_Jardim_dos_Ipês_III.xlsx'
xls = pd.ExcelFile(file_path)
print("Abas no pandas:", xls.sheet_names)
