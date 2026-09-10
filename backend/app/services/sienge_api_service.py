import urllib.parse
from typing import Any, Dict, List, Optional

from app.services.sienge_client import SiengeClient


class SiengeApiService:
    """Métodos de domínio v1/bulk; HTTP delegado a SiengeClient."""

    def __init__(self, subdomain: str, auth_string: str):
        self._client = SiengeClient.from_auth_string(subdomain, auth_string)

    @property
    def base_url(self) -> str:
        return self._client.api_v1_base_url

    @property
    def bulk_base_url(self) -> str:
        return self._client.bulk_base_url

    def _fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        return self._client.get_json(url, retries=3, not_found_ok=True)

    def get_bills(self, start_date: str, end_date: str, cost_center_id: str) -> List[Dict[str, Any]]:
        bills = []
        offset = 0
        limit = 200
        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "startDate": start_date,
                "endDate": end_date,
                "costCenterId": cost_center_id,
            }
            qs = urllib.parse.urlencode(params)
            url = f"{self.base_url}/bills?{qs}"

            data = self._fetch_json(url)
            if not data or "results" not in data or not data["results"]:
                break

            bills.extend(data["results"])
            if len(data["results"]) < limit:
                break
            offset += limit

        return bills

    def get_bill_installments(self, bill_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/bills/{bill_id}/installments"
        data = self._fetch_json(url)
        if data and "results" in data:
            return data["results"]
        return []

    def get_bill_budget_categories(self, bill_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/bills/{bill_id}/budget-categories"
        data = self._fetch_json(url)
        if data and "results" in data:
            return data["results"]
        return []

    def get_bulk_income(
        self,
        company_id: int,
        start_date: str,
        end_date: str,
        correction_date: str = None,
    ) -> List[Dict[str, Any]]:
        import datetime

        if not correction_date:
            correction_date = datetime.datetime.now().strftime("%Y-%m-%d")

        incomes = []
        offset = 0
        limit = 100
        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "startDate": start_date,
                "endDate": end_date,
                "selectionType": "P",
                "correctionIndexerId": 0,
                "correctionDate": correction_date,
                "companyId": company_id,
            }
            qs = urllib.parse.urlencode(params)
            url = f"{self.bulk_base_url}/income?{qs}"

            data = self._fetch_json(url)
            if not data or "data" not in data or not data["data"]:
                break

            incomes.extend(data["data"])
            if len(data["data"]) < limit:
                break
            offset += limit

        return incomes
