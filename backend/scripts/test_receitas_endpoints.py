import urllib.request
import urllib.parse
import base64
import json

def fetch_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error {url}: {e}")
        return None

def test_bills():
    base_url = "https://api.sienge.com.br/mouraleite/public/api/v1"
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {base64_auth}",
        "Accept": "application/json"
    }
    
    print("\nFetching /bills...")
    params = {
        "startDate": "2026-06-01",
        "endDate": "2026-06-30",
        "limit": 200
    }
    qs = urllib.parse.urlencode(params)
    res = fetch_json(f"{base_url}/bills?{qs}", headers)
    if res and res.get('results'):
        print(f"Found {len(res['results'])} bills.")
        origins = set(r.get('originId') for r in res['results'])
        print(f"Origins: {origins}")
        
if __name__ == "__main__":
    test_bills()
