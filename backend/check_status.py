import urllib.request
import json

from app.services.sienge_client import build_auth_header, bulk_base_url
from app.core.config import settings

SIENGE_BASE_URL = bulk_base_url()

def get_auth_header():
    return build_auth_header(settings.SIENGE_USER, settings.SIENGE_PASS)

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
