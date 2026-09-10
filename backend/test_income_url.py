import json
from app.services.sienge_sync import _fetch_paginated_bulk, SIENGE_BASE_URL

cc_id_sienge = 16111
url = f"{SIENGE_BASE_URL}/income?startDate=2001-01-01&endDate=2050-12-31&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc_id_sienge}&withAuthorizations=false&withBankMovements=true"

try:
    for page in _fetch_paginated_bulk(url):
        for item in page:
            print(json.dumps(item, indent=2))
except Exception as e:
    print('Error:', e)
