import sys, os; sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from app.models.unit import Unit
from app.models.actual_transaction import ActualTransaction
from collections import defaultdict
import re

db = SessionLocal()
transactions = db.query(ActualTransaction).filter(
    ActualTransaction.cost_center_id == 206, 
    ActualTransaction.transaction_type == 'INCOME'
).all()

bill_dates = defaultdict(list)
bill_values = defaultdict(float)

for t in transactions:
    match = re.search(r'INC-(\d+)-', t.source_id)
    if match and t.transaction_date:
        bill_id = match.group(1)
        bill_dates[bill_id].append(t.transaction_date)
        if 'FCST' not in t.source_id:
            pass
        bill_values[bill_id] += t.value

bins_val = {'Até 6x': 0, 'Até 12x': 0, 'Até 24x': 0, 'Até 36x': 0, 'Até 48x': 0, 'Até 60x': 0, 'Até 120x': 0, 'Até 156x': 0, 'Até 180x': 0}

for bill_id, dates in bill_dates.items():
    min_date = min(dates)
    max_date = max(dates)
    months = (max_date - min_date).days / 30.416
    val = bill_values[bill_id]
    
    if months <= 6: bins_val['Até 6x'] += val
    elif months <= 12: bins_val['Até 12x'] += val
    elif months <= 24: bins_val['Até 24x'] += val
    elif months <= 36: bins_val['Até 36x'] += val
    elif months <= 48: bins_val['Até 48x'] += val
    elif months <= 60: bins_val['Até 60x'] += val
    elif months <= 120: bins_val['Até 120x'] += val
    elif months <= 156: bins_val['Até 156x'] += val
    else: bins_val['Até 180x'] += val

total_val = sum(bins_val.values())
if total_val > 0:
    for k, v in bins_val.items():
        print(f'{k}: ({(v/total_val)*100:.1f}%)')
