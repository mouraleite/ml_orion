import urllib.request
import urllib.parse
import base64
import json

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
            total_receipts = 0
            
            for item in data:
                receipts = item.get('receipts', [])
                for receipt in receipts:
                    # Filter by payment date to be sure
                    if receipt.get('paymentDate', '').startswith('2026-01'):
                        total_receipts += 1
                        # Wait, what amount does the user use? netAmount? grossAmount?
                        # Let's sum netAmount
                        total_net_amount += float(receipt.get('netAmount', 0))
                        
            print(f"Total receipts in Jan: {total_receipts}")
            print(f"Total net amount: {total_net_amount}")
            
            # Print an example receipt
            if data and data[0].get('receipts'):
                print("\nExample receipt:")
                print(json.dumps(data[0]['receipts'][0], indent=2))
                
    except Exception as e:
        print(f"Erro /income: {e}")

if __name__ == "__main__":
    test_user_query()
