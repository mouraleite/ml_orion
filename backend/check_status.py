import urllib.request
import json
import base64

SIENGE_BASE_URL = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1"
SIENGE_USER = "mouraleite-contas-a-pagar"
SIENGE_PASS = "U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"

def get_auth_header():
    auth_str = f"{SIENGE_USER}:{SIENGE_PASS}"
    b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    return {"Authorization": f"Basic {b64_auth}"}

def check_structure():
    url = f"{SIENGE_BASE_URL}/income?startDate=2019-01-01&endDate=2019-12-31&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&limit=1"
    headers = get_auth_header()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get("data", data.get("results", []))
            if items:
                print("Keys:", items[0].keys())
                print("Item:", json.dumps(items[0], indent=2))
    except urllib.error.HTTPError as e:
        print(f"Erro {e.code}: {e.read().decode('utf-8')}")

if __name__ == "__main__":
    check_structure()
