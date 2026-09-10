import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.api.routes.tracking import _calc_actuals_for_cc
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from collections import defaultdict

db = SessionLocal()

print("Checking slice_monthly_cf for 14304")
try:
    c = db.query(CostCenter).filter(CostCenter.id_sienge == '14304').first()
    macro_prefix = '143'
    pct = 0.43502
    
    macro_monthly_cf = defaultdict(float)
    macro_monthly_rev = defaultdict(float)
    
    all_ccs = db.query(CostCenter).filter(CostCenter.id_sienge.like(f"{macro_prefix}%")).all()
    for sub_cc in all_ccs:
        act = _calc_actuals_for_cc(db, sub_cc.id, None, 1.0, 1.0, {})
        for m, v in act.get("monthly_net_cf_real", {}).items(): macro_monthly_cf[m] += v
        for m, v in act.get("monthly_revenues_real", {}).items(): macro_monthly_rev[m] += v
            
    native_act = _calc_actuals_for_cc(db, c.id, None, 1.0, 1.0, {})
    
    slice_monthly_cf = defaultdict(float)
    all_months = set(macro_monthly_cf.keys()) | set(native_act.get("monthly_net_cf_real", {}).keys())
    
    print("Mês | Receita Nativa | Custo Macro | Custo Rateado | Saldo")
    total_saldo = 0
    negatives = 0
    for m in sorted(all_months):
        if m == "N/A": continue
        m_rev = macro_monthly_rev.get(m, 0.0)
        m_cf = macro_monthly_cf.get(m, 0.0)
        m_costs = m_rev - m_cf
        m_slice_costs = m_costs * pct
        
        m_native_rev = native_act.get("monthly_revenues_real", {}).get(m, 0.0)
        saldo = m_native_rev - m_slice_costs
        slice_monthly_cf[m] = saldo
        total_saldo += saldo
        if saldo < 0: negatives += 1
        
        if saldo < 0 or m_native_rev > 0 or m_slice_costs > 0:
            print(f"{m} | {m_native_rev:.2f} | {m_costs:.2f} | {m_slice_costs:.2f} | {saldo:.2f}")

    print(f"\nNegatives: {negatives}, Total Saldo: {total_saldo}")
        
except Exception as e:
    import traceback
    traceback.print_exc()

