import urllib.request
import urllib.parse
import base64
import json
from collections import defaultdict

def test_user_query():
    url = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/income?startDate=2026-01-01&endDate=2026-01-31&selectionType=P&correctionIndexerId=0&correctionDate=2025-09-01&companyId=1"
    
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {base64_auth}")

    try:
        with urllib.request.urlopen(req) as response:
            payload = json.loads(response.read().decode('utf-8'))
            data = payload.get('data', [])
            
            total_net_amount = 0.0
            
            for item in data:
                receipts = item.get('receipts', [])
                for receipt in receipts:
                    if receipt.get('paymentDate', '').startswith('2026-01'):
                        bank_movements = receipt.get('bankMovements', [])
                        for bm in bank_movements:
                            op_type = bm.get('operationType')
                            amount = float(bm.get('correctedAmount', 0))
                            
                            categories = bm.get('financialCategories', [])
                            for cat in categories:
                                cc_id = str(cat.get('costCenterId', ''))
                                if cc_id == '11300':
                                    rate = float(cat.get('financialCategoryRate', 100)) / 100.0
                                    val = amount * rate
                                    if op_type == 'E':
                                        total_net_amount += val
                                    elif op_type == 'S':
                                        total_net_amount -= val
                                    
            print(f"Total Receitas for Empreendimento 11300 (Jan 2026): R$ {total_net_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
    except Exception as e:
        print(f"Erro /income: {e}")

if __name__ == "__main__":
    test_user_query()
