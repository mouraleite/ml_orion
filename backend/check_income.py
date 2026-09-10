import urllib.request
import json
import base64

url = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/income?startDate=2001-01-01&endDate=2050-12-31&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId=14100"

auth_str = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
encoded = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
headers = {"Authorization": f"Basic {encoded}"}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    print("Status:", response.status)
    data = json.loads(response.read().decode('utf-8'))
    results = data.get("data", data.get("results", []))
    print(f"Total top-level income items: {len(results)}")
    
    if len(results) > 0:
        first = results[0]
        print("Fields in item:", list(first.keys()))
        print("Item billId:", first.get("billId"), "Amount:", first.get("originalAmount"))
        
        # Check receipts
        receipts = first.get("receipts", [])
        print("Number of receipts in first item:", len(receipts))
        
        if receipts:
            print("Fields in receipt:", list(receipts[0].keys()))
            bms = receipts[0].get("bankMovements", [])
            print("Number of bankMovements in first receipt:", len(bms))
            
            if bms:
                fcs = bms[0].get("financialCategories", [])
                print("Number of financialCategories in first bankMovement:", len(fcs))
                if fcs:
                    print("First financialCategory:", fcs[0])
