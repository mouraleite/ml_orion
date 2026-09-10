import urllib.request
import json
import base64

url = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/sales?enterpriseId=14100&createdAfter=2001-12-31&createdBefore=2050-12-31&situation=SOLD"

auth_str = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
encoded = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
headers = {"Authorization": f"Basic {encoded}"}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
    results = data.get("data", data.get("results", []))
    print(f"Total: {len(results)}")
    if results:
        print("First Situation:", results[0].get("situation"))
        print("Total selling value:", results[0].get("totalSellingValue"))
