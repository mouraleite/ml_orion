import urllib.request
import json
import base64

url = "https://api.sienge.com.br/mouraleite/public/api/v1/units?limit=5&offset=0"

auth_str = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
encoded = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
headers = {"Authorization": f"Basic {encoded}"}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        results = data.get("data", data.get("results", []))
        print(f"Total: {len(results)}")
        if results:
            print("First Unit Name:", results[0].get("name"))
            print("Commercial Stock:", results[0].get("commercialStock"))
            print("Private Area:", results[0].get("privateArea"))
except Exception as e:
    print("Error:", e)
