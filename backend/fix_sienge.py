import re

with open('app/services/sienge_sync.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of sync_outcomes
start_idx = content.find('def sync_outcomes')
end_idx = content.find('def sync_payables_forecast')

if start_idx != -1 and end_idx != -1:
    new_code = """def sync_outcomes(db: Session, cc: CostCenter, start_date: str, end_date: str):
    url = f"{SIENGE_BASE_URL}/outcome?startDate={start_date}&endDate={end_date}&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc.id_sienge}&withAuthorizations=false&withBankMovements=true"
    
    existing = {
        r.source_id: r 
        for r in db.query(ActualTransaction).filter_by(cost_center_id=cc.id, transaction_type="OUTCOME").all()
    }
    
    for page in _fetch_paginated_bulk(url):
        for item in page:
            bill_id = item.get('billId', item.get('documentId'))
            cats = item.get("paymentsCategories", [])
            if not cats:
                cats = item.get("financialCategories", [])
                
            cat_name = "Obras"
            is_for_cc = False
            apportionment_ratio = 1.0
            
            if cats:
                total_cats_value = sum(float(c.get("value", 0)) for c in cats)
                for c in cats:
                    if str(c.get("costCenterId")) == str(cc.id_sienge):
                        is_for_cc = True
                        cat_name = c.get("financialCategoryName", "Obras")
                        perc = c.get("percentage")
                        if perc is not None:
                            apportionment_ratio = float(perc) / 100.0
                        elif total_cats_value > 0:
                            apportionment_ratio = float(c.get("value", 0)) / total_cats_value
                        break
                        
            if cats and not is_for_cc:
                continue

            for pmt in item.get("payments", []):
                pmt_id = pmt.get("sequencialNumber", pmt.get("id", "0"))
                source_id = f"OUT-{bill_id}-PMT-{pmt_id}"
                value = float(pmt.get("netAmount", pmt.get("grossAmount", 0))) * apportionment_ratio
                
                date_str = pmt.get("paymentDate")
                if not date_str:
                    continue
                from datetime import datetime
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                
                record = existing.get(source_id)
                if not record:
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="OUTCOME"
                    )
                    db.add(record)
                    existing[source_id] = record
                    
                record.transaction_date = dt
                record.value = value
                record.category = cat_name
                
    db.commit()

def sync_incomes(db: Session, cc: CostCenter, start_date: str, end_date: str):
    url = f"{SIENGE_BASE_URL}/income?startDate={start_date}&endDate={end_date}&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc.id_sienge}&withAuthorizations=false&withBankMovements=true"
    
    existing = {
        r.source_id: r 
        for r in db.query(ActualTransaction).filter_by(cost_center_id=cc.id, transaction_type="INCOME").all()
    }
    
    for page in _fetch_paginated_bulk(url):
        for item in page:
            bill_id = item.get('billId', item.get('documentId'))
            
            for rec in item.get('receipts', []):
                fcs = rec.get("financialCategories", [])
                if not fcs:
                    fcs = item.get("financialCategories", [])
                    
                cat_name = "Recebimento"
                is_for_cc = False
                apportionment_ratio = 1.0
                
                if fcs:
                    total_cats_value = sum(float(fc.get("value", 0)) for fc in fcs)
                    for fc in fcs:
                        if str(fc.get("costCenterId")) == str(cc.id_sienge):
                            is_for_cc = True
                            cat_name = fc.get("financialCategoryName", "Recebimento")
                            perc = fc.get("percentage")
                            if perc is not None:
                                apportionment_ratio = float(perc) / 100.0
                            elif total_cats_value > 0:
                                apportionment_ratio = float(fc.get("value", 0)) / total_cats_value
                            break
                        
                if fcs and not is_for_cc:
                    continue
                    
                rec_id = rec.get("sequencialNumber", rec.get("id", "0"))
                source_id = f"INC-{bill_id}-REC-{rec_id}"
                value = float(rec.get("netAmount", rec.get("grossAmount", 0))) * apportionment_ratio
                
                date_str = rec.get("receiptDate")
                if not date_str:
                    continue
                from datetime import datetime
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                
                record = existing.get(source_id)
                if not record:
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="INCOME"
                    )
                    db.add(record)
                    existing[source_id] = record
                    
                record.transaction_date = dt
                record.value = value
                record.category = cat_name
                
    db.commit()

def sync_receivables_forecast(db: Session, cc: CostCenter):
    from datetime import datetime
    current_year = datetime.now().year
    from sqlalchemy import text as sa_text
    db.execute(
        sa_text("DELETE FROM actual_transactions WHERE cost_center_id=:cc AND transaction_type='INCOME' AND is_forecast=1"),
        {"cc": cc.id}
    )
    db.commit()

    count = 0
    try:
        for offset in range(15):
            year = current_year + offset
            start_date = datetime.now().strftime("%Y-%m-%d") if offset == 0 else f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            url = f"{SIENGE_BASE_URL}/income?startDate={start_date}&endDate={end_date}&selectionType=D&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc.id_sienge}"
            print(f"[Forecast] Buscando contas a receber futuras ({year}) para CC {cc.id_sienge}...")
            
            year_count = 0
            for page in _fetch_paginated_bulk(url):
                for item in page:
                    bill_id = item.get('billId')
                    installment_id = item.get('installmentId', item.get('installmentNumber', count))
                    
                    due_date_str = item.get('dueDate') or item.get('installmentBaseDate')
                    
                    bal = item.get('balanceAmount')
                    corr = item.get('correctedBalanceAmount')
                    
                    if bal is not None:
                        amount = max(float(bal or 0), float(corr or 0))
                    else:
                        amount = float(item.get('originalAmount') or 0)
                    
                    if not due_date_str or amount <= 0:
                        continue
                    
                    try:
                        dt = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
                    except Exception:
                        continue

                    fcs = item.get("receiptsCategories", item.get("financialCategories", []))
                    cat_name = "Receita de Venda de Lotes"
                    is_for_cc = len(fcs) == 0
                    
                    for fc in fcs:
                        if str(fc.get("costCenterId")) == str(cc.id_sienge):
                            is_for_cc = True
                            cat_name = fc.get("financialCategoryName", cat_name)
                            break
                    
                    if not is_for_cc:
                        continue

                    source_id = f"FCST-INC-{bill_id}-{installment_id}"
                    
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="INCOME",
                        transaction_date=dt,
                        value=amount,
                        category=cat_name,
                        is_forecast=True
                    )
                    db.add(record)
                    count += 1
                    year_count += 1
            
            print(f"[Forecast] Ano {year}: {year_count} parcelas de recebimento")
            
    except Exception as e:
        print(f"[Sienge Sync] Exception forecast income: {str(e)}")

    db.commit()
    print(f"[Forecast] {count} parcelas de recebimento futuras sincronizadas para CC {cc.id_sienge}")

"""
    
    content = content[:start_idx] + new_code + content[end_idx:]
    with open('app/services/sienge_sync.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Could not find blocks")
