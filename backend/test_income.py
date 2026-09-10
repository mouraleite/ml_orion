import urllib.request
import json
import base64

url = "https://api.sienge.com.br/mouraleite/public/api/bulk-data/v1/income?startDate=2001-01-01&endDate=2050-12-31&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId=14100&limit=1"

auth_str = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
encoded = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
headers = {"Authorization": f"Basic {encoded}"}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        data = json.loads(response.read().decode('utf-8'))
        results = data.get("data", data.get("results", []))
        print("Total results retrieved in limit=1:", len(results))
        if results:
            print("Keys in first item:", list(results[0].keys()))
            print("First item sample (dueDate, issueDate):", results[0].get("dueDate"), results[0].get("issueDate"))
        else:
            print("No items returned.")
except Exception as e:
    print("Error:", str(e))
