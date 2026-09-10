import urllib.request
import urllib.parse
import base64
import json
import datetime

def test_bulk_outcome():
    base_url = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/outcome"
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    params = {
        "startDate": "2026-01-01",
        "endDate": "2026-06-30",
        "selectionType": "P",
        "correctionIndexerId": 0,
        "correctionDate": today,
        "completeBills": "S", # Títulos Completos!
        "companyId": 1,
        "withBankMovements": "true",
        "limit": 5
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"
    print(url)
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {base64_auth}")

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("Status /outcome: 200 OK")
            print(f"Total results: {len(data.get('results', []))}")
            if data.get('results'):
                print(json.dumps(data['results'][0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Erro /outcome: {e}")
        if hasattr(e, 'read'):
            try:
                print(e.read().decode('utf-8'))
            except:
                pass

if __name__ == "__main__":
    test_bulk_outcome()
