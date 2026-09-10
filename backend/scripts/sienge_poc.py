import urllib.request
import urllib.parse
import base64
import json
import time
import concurrent.futures
from collections import defaultdict
import sqlite3

AUTH_STRING = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
BASE64_AUTH = base64.b64encode(AUTH_STRING.encode('ascii')).decode('ascii')
BASE_URL = "https://api.sienge.com.br/mouraleite/public/api/v1"

def fetch_json(url):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {BASE64_AUTH}")
    for _ in range(3):
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            time.sleep(1)
    return None

def get_bills_for_cc(cc_id):
    bills = []
    offset = 0
    while True:
        params = {
            "limit": 100,
            "offset": offset,
            "startDate": "2026-01-01",
            "endDate": "2026-12-31",
            "costCenterId": cc_id
        }
        qs = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/bills?{qs}"
        data = fetch_json(url)
        if not data or 'results' not in data or not data['results']:
            break
        bills.extend(data['results'])
        if len(data['results']) < 100:
            break
        offset += 100
    return bills

def process_bill(bill):
    bill_id = bill['id']
    
    inst_url = f"{BASE_URL}/bills/{bill_id}/installments"
    inst_data = fetch_json(inst_url)
    if not inst_data or 'results' not in inst_data:
        return []
    
    installments = inst_data['results']
    
    bud_url = f"{BASE_URL}/bills/{bill_id}/budget-categories"
    bud_data = fetch_json(bud_url)
    categories = bud_data.get('results', []) if bud_data else []
    
    results = []
    for inst in installments:
        if inst.get('situation') != 'Totalmente paga':
            continue
            
        amount = inst.get('amount', 0)
        date = inst.get('paymentDate') or inst.get('dueDate') or inst.get('baseDate')
        if not date or not str(date).startswith('2026'):
            continue
            
        month = str(date)[:7]
        
        for cat in categories:
            cc_id = str(cat.get('costCenterId')) # Use string to match id_sienge
            cat_id = str(cat.get('paymentCategoriesId'))
            perc = cat.get('percentage', 100.0) / 100.0
            cat_amount = amount * perc
            
            results.append({
                'bill_id': bill_id,
                'cc_id': cc_id,
                'cat_id': cat_id,
                'month': month,
                'amount': cat_amount
            })
            
    return results

def run_poc():
    conn = sqlite3.connect('viabilidades.db')
    c = conn.cursor()
    c.execute('SELECT id_sienge, nome, custom_data FROM cost_centers')
    ccs = c.fetchall()
    cc_map = {}
    for row in ccs:
        try:
            custom = json.loads(row[2]) if row[2] else {}
            if str(custom.get('__id_empresa')) == '1':
                nome = row[1] or custom.get('nome') or 'Unknown'
                id_sienge = str(row[0])
                cc_map[id_sienge] = nome
        except:
            pass
            
    cc_ids = list(cc_map.keys())
    print(f"Total CCs para Empresa 1 (11300): {len(cc_ids)}")
    
    all_bills = []
    print("Buscando bills por CC...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_cc = {executor.submit(get_bills_for_cc, cc): cc for cc in cc_ids}
        for future in concurrent.futures.as_completed(future_to_cc):
            bills = future.result()
            all_bills.extend(bills)
            
    unique_bills = {b['id']: b for b in all_bills}.values()
    print(f"Total de contas únicas encontradas: {len(unique_bills)}")
    
    if len(unique_bills) == 0:
        print("Nenhuma conta encontrada.")
        return

    print("Processando parcelas e rateios...")
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_bill = {executor.submit(process_bill, b): b for b in unique_bills}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_bill)):
            if i % 100 == 0 and i > 0:
                print(f"Processadas {i} contas...")
            res = future.result()
            all_results.extend(res)
            
    summary = defaultdict(lambda: defaultdict(float))
    for r in all_results:
        # Check if the CC belongs to Empresa 1
        if str(r['cc_id']) in cc_map:
            summary[r['month']][cc_map[str(r['cc_id'])]] += r['amount']
            
    print("\n--- RESUMO DFC POR CENTRO DE CUSTO (POC) ---")
    months = sorted(list(summary.keys()))
    for m in months:
        print(f"\nMês: {m}")
        total_mes = 0
        for cc_name, val in sorted(summary[m].items()):
            print(f"  {cc_name}: R$ {val:,.2f}")
            total_mes += val
        print(f"  TOTAL DO MÊS: R$ {total_mes:,.2f}")
        
    with open('poc_sienge_11300.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print("\nConcluído! Salvo em poc_sienge_11300.json")

if __name__ == "__main__":
    run_poc()
