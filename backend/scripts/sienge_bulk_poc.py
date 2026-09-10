import urllib.request
import urllib.parse
import base64
import json
import datetime
from collections import defaultdict

AUTH_STRING = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
BASE64_AUTH = base64.b64encode(AUTH_STRING.encode('ascii')).decode('ascii')
BASE_URL = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/outcome"

def run_poc():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # selectionType D = Data de vencimento
    params = {
        "startDate": "2026-01-01",
        "endDate": "2026-06-30",
        "selectionType": "D",
        "correctionIndexerId": 1,
        "correctionDate": today,
        "withBankMovements": "true",
        "limit": 10,
        "offset": 0
    }
    qs = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{qs}"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {BASE64_AUTH}")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            results = data.get('results', [])
            print(f"Total de resultados na primeira pagina (vencimento 2026): {len(results)}")
            
            if results:
                with open('bulk_outcome_sample.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print("Salvo em bulk_outcome_sample.json")
    except Exception as e:
        print(f"Erro na requisição: {e}")
        if hasattr(e, 'read'):
            try:
                print(e.read().decode('utf-8'))
            except:
                pass

if __name__ == "__main__":
    run_poc()
