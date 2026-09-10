import pandas as pd
import os
import sys

# Ajustar o caminho para importar o app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.main
from app.db.database import SessionLocal
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from sqlalchemy import extract

def main():
    print("Conectando ao banco de dados...")
    db = SessionLocal()

    # 1. Carregar Realizado do Banco de Dados (Filtrado por SP-MIG e Ano 2026)
    print("Carregando transações do banco de dados...")
    reais = db.query(ActualTransaction).filter(
        extract('year', ActualTransaction.transaction_date) == 2026,
        ActualTransaction.is_forecast == False,
        ActualTransaction.source_id.like('SP-MIG-%')
    ).all()

    ccs = {cc.id: cc for cc in db.query(CostCenter).all()}
    db_cc_totals = {}
    
    for tx in reais:
        cc = ccs.get(tx.cost_center_id)
        if cc:
            empresa = cc.custom_data.get('__id_empresa') if cc.custom_data else None
            if str(empresa) == '1':
                cc_code = str(cc.id_sienge).strip() if cc.id_sienge else "SEM_CODIGO"
                if cc_code not in db_cc_totals:
                    db_cc_totals[cc_code] = {'INCOME': 0, 'OUTCOME': 0}
                db_cc_totals[cc_code][tx.transaction_type] += tx.value

    # 2. Carregar Realizado da Planilha "Agrupamento empresa 1 - realizado.xlsx"
    print("Carregando planilha do usuário...")
    excel_path = r'C:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\Agrupamento empresa 1 - realizado.xlsx'
    df = pd.read_excel(excel_path, header=None)

    excel_cc_totals = {}
    current_cc = None
    total_col_real = None

    for idx in range(len(df)):
        row = df.iloc[idx]
        row_vals = [str(x).strip() for x in row if pd.notna(x)]
        
        # Detectar bloco de Centro de Custo iterando sobre os valores não nulos
        if len(row_vals) > 0 and 'Tipo de an' in row_vals[0]:
            for i, val in enumerate(row_vals):
                if 'Centro de custo' in val:
                    if i + 1 < len(row_vals):
                        val_3 = row_vals[i+1]
                        if ' - ' in val_3:
                            current_cc = val_3.split(' - ')[0].strip()
                        else:
                            current_cc = val_3
                        total_col_real = None
                        break
                
        val_0 = str(row[0]).strip()
        if val_0 == 'Código' or val_0 == 'Cdigo' or 'Código' in val_0 or 'Cdigo' in val_0:
            mes_idx = idx - 1
            row_mes = df.iloc[mes_idx]
            
            total_idx = -1
            for i, val in enumerate(row_mes):
                if pd.notna(val) and 'total do' in str(val).lower():
                    total_idx = i
                    break
                    
            if total_idx != -1:
                for j in range(max(0, total_idx-2), min(len(df.columns), total_idx+3)):
                    val_11 = str(df.iloc[idx, j]).strip().lower()
                    if 'realizado' in val_11 and total_col_real is None:
                        total_col_real = j
                        
        if current_cc is not None and total_col_real is not None:
            if val_0 == '1' or 'ENTRADAS' in str(row.values).upper():
                v = row[total_col_real]
                if pd.notna(v) and str(row[0]).strip() == '1':
                    if current_cc not in excel_cc_totals:
                        excel_cc_totals[current_cc] = {'INCOME': 0, 'OUTCOME': 0}
                    try:
                        excel_cc_totals[current_cc]['INCOME'] += float(v)
                    except:
                        pass
                        
            if val_0 == '2' or 'SAÍDAS' in str(row.values).upper() or 'SADAS' in str(row.values).upper() or 'CUSTOS' in str(row.values).upper():
                v = row[total_col_real]
                if pd.notna(v) and str(row[0]).strip() == '2':
                    if current_cc not in excel_cc_totals:
                        excel_cc_totals[current_cc] = {'INCOME': 0, 'OUTCOME': 0}
                    try:
                        excel_cc_totals[current_cc]['OUTCOME'] += float(v)
                    except:
                        pass

    # 3. Cruzar os dados e gerar DataFrame final
    print("Cruzando dados...")
    data = []
    todos_ccs = set(db_cc_totals.keys()).union(excel_cc_totals.keys())
    
    for code in sorted(todos_ccs):
        db_r = db_cc_totals.get(code, {}).get('INCOME', 0)
        db_d = db_cc_totals.get(code, {}).get('OUTCOME', 0)
        ex_r = excel_cc_totals.get(code, {}).get('INCOME', 0)
        ex_d = excel_cc_totals.get(code, {}).get('OUTCOME', 0)
        
        diff_r = db_r - ex_r
        diff_d = db_d - ex_d
        
        # Opcional: Adicionar Nome do CC buscando no db
        nome_cc = ""
        for c in ccs.values():
            if str(c.id_sienge).strip() == code:
                nome_cc = c.nome
                break
                
        data.append({
            'Código CC': code,
            'Nome CC': nome_cc,
            'Receita DB': db_r,
            'Receita Excel': ex_r,
            'Diferença Receita': diff_r,
            'Despesa DB': db_d,
            'Despesa Excel': ex_d,
            'Diferença Despesa': diff_d,
        })

    df_out = pd.DataFrame(data)
    
    # 4. Salvar
    out_path = r'C:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\Comparativo_CC_Realizado.xlsx'
    df_out.to_excel(out_path, index=False)
    print(f"Planilha gerada com sucesso em: {out_path}")

if __name__ == '__main__':
    main()
