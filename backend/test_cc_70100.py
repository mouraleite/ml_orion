import json
from app.services.sienge_sync import _fetch_paginated_bulk, SIENGE_BASE_URL

cc_id_sienge = 70100
url = f"{SIENGE_BASE_URL}/outcome?startDate=2026-01-01&endDate=2026-12-31&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc_id_sienge}&withAuthorizations=false&withBankMovements=true"

try:
    for page in _fetch_paginated_bulk(url):
        for item in page:
            print("Found Item:")
            print(json.dumps(item, indent=2))
            break # Just one to look at the structure
        break
except Exception as e:
    print('Error:', e)
