import sys
sys.path.insert(0, '.')

import app.main
import pandas as pd
import re
from app.db.database import SessionLocal
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.cost_center import CostCenter
from collections import defaultdict

db = SessionLocal()

# Ler Excel
f = r'C:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\Agrupamento empresa 1.xlsx'
df = pd.read_excel(f, header=None)

excel_ccs = []
i = 0
while i < len(df):
    row = df.iloc[i]
    if str(row[11]).strip() == 'Centro de custo':
        cc_nome = str(row[16]).strip()
        m = re.match(r'^(\d+)', cc_nome)
        sid = m.group(1) if m else None
        rec = 0
        desp = 0
        for j in range(i+1, min(i+20, len(df))):
            r = df.iloc[j]
            if 'ENTRADAS' in str(r[1]).upper() or 'RECEITAS' in str(r[1]).upper():
                rec = float(r[5]) if pd.notna(r[5]) else 0
            if 'SA' in str(r[1]).upper() and 'DESPESAS' in str(r[1]).upper():
                desp = float(r[5]) if pd.notna(r[5]) else 0
                excel_ccs.append({'id_sienge': sid, 'cc': cc_nome, 'desp_jan': desp, 'rec_jan': rec})
                break
    i += 1

print(f"Total CCs no Excel: {len(excel_ccs)}")

# Buscar no banco itens do orcamento de despesas (id=5)
items = db.query(OrcamentoItem).filter_by(orcamento_id=5).all()
cc_id_to_erp = {cc.id: cc for cc in db.query(CostCenter).all()}

db_desp_per_cc = defaultdict(float)
for item in items:
    cc = cc_id_to_erp.get(item.produto_id)
    if cc and cc.id_sienge:
        db_desp_per_cc[str(cc.id_sienge)] += (item.jan or 0)

# Comparar CC a CC
print("\n=== CCs com diferença > R$1 ===")
print(f"{'id_sienge':<10} | {'CC Nome':<45} | {'Excel':>12} | {'ERP DB':>12} | {'Diferença':>12}")
print("-" * 100)

total_excel = 0
total_db = 0
for ec in sorted(excel_ccs, key=lambda x: abs((db_desp_per_cc.get(x['id_sienge'],0) - x['desp_jan'])), reverse=True):
    sid = ec['id_sienge']
    db_val = db_desp_per_cc.get(sid, 0)
    diff = db_val - ec['desp_jan']
    total_excel += ec['desp_jan']
    total_db += db_val
    if abs(diff) > 1:
        nome_curto = ec['cc'][:45]
        print(f"{sid:<10} | {nome_curto:<45} | {ec['desp_jan']:>12.2f} | {db_val:>12.2f} | {diff:>12.2f}")

print("-" * 100)
print(f"{'TOTAL':<10} | {' '*45} | {total_excel:>12.2f} | {total_db:>12.2f} | {total_db - total_excel:>12.2f}")

# CCs no DB com empresa=1 que NAO estao no Excel
print("\n=== CCs no ERP Empresa 1 que NAO estao no Excel do Sienge ===")
ids_excel = set(ec['id_sienge'] for ec in excel_ccs if ec['id_sienge'])
for sid, val in db_desp_per_cc.items():
    if sid not in ids_excel and val > 0:
        cc = next((cc for cc in db.query(CostCenter).all() if str(cc.id_sienge) == sid), None)
        if cc:
            empresa = cc.custom_data.get('__id_empresa') if cc.custom_data else None
            if str(empresa) == '1':
                print(f"  id_sienge={sid}, nome={cc.nome}, desp_jan={val:.2f}")
