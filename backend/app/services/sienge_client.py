"""
Cliente HTTP unificado para a API Sienge (v1 + bulk-data).

Transporte apenas: auth, paginação e GET JSON. Mapeamento para orçamento/forecast
permanece em sienge_sync, integracao_sienge e erp_integration.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Generator, Iterator, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_BULK_LIMIT = 200
DEFAULT_V1_LIMIT = 200


def bulk_base_url(subdomain: str | None = None) -> str:
    sub = subdomain or settings.SIENGE_SUBDOMAIN
    return f"https://api.sienge.com.br/{sub}/public/api/bulk-data/v1"


def api_v1_base_url(subdomain: str | None = None) -> str:
    sub = subdomain or settings.SIENGE_SUBDOMAIN
    return f"https://api.sienge.com.br/{sub}/public/api/v1"


def build_auth_header(user: str, password: str) -> dict[str, str]:
    auth_str = f"{user}:{password}"
    encoded = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


def get_default_client() -> "SiengeClient":
    return SiengeClient(
        subdomain=settings.SIENGE_SUBDOMAIN,
        user=settings.SIENGE_USER,
        password=settings.SIENGE_PASS,
    )


def _safe_record_sienge_call(url: str, method: str, status_code: int | None, started: float) -> None:
    """Registra a chamada. Nunca propaga erro nem altera o retorno do HTTP."""
    try:
        from app.services.sienge_usage import record_sienge_http_call

        record_sienge_http_call(
            url=url,
            method=method,
            status_code=status_code,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except Exception:
        logger.warning("Falha ao gravar log de consumo da API Sienge")


class SiengeClient:
    def __init__(self, subdomain: str, user: str, password: str):
        self.subdomain = subdomain
        self.user = user
        self.password = password
        self._headers = {
            **build_auth_header(user, password),
            "Accept": "application/json",
        }

    @property
    def bulk_base_url(self) -> str:
        return bulk_base_url(self.subdomain)

    @property
    def api_v1_base_url(self) -> str:
        return api_v1_base_url(self.subdomain)

    def auth_headers(self) -> dict[str, str]:
        return dict(self._headers)

    def get_json(
        self,
        url: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = 1,
        not_found_ok: bool = False,
    ) -> Optional[dict[str, Any]]:
        req = urllib.request.Request(url, headers=self._headers)
        for attempt in range(max(1, retries)):
            started = time.perf_counter()
            recorded = False
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    _safe_record_sienge_call(url, "GET", response.status, started)
                    recorded = True
                    if response.status != 200:
                        logger.warning("Sienge HTTP %s em %s", response.status, url)
                        return None
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if not recorded:
                    _safe_record_sienge_call(url, "GET", e.code, started)
                if not_found_ok and e.code == 404:
                    return None
                logger.warning(
                    "Sienge HTTPError %s em %s (tentativa %s/%s)",
                    e.code,
                    url,
                    attempt + 1,
                    retries,
                )
                if attempt + 1 >= retries:
                    return None
                time.sleep(2**attempt)
            except Exception as e:
                if not recorded:
                    _safe_record_sienge_call(url, "GET", None, started)
                logger.warning(
                    "Sienge erro em %s (tentativa %s/%s): %s",
                    url,
                    attempt + 1,
                    retries,
                    e,
                )
                if attempt + 1 >= retries:
                    return None
                time.sleep(2**attempt)
        return None

    def paginate_bulk(
        self,
        url: str,
        *,
        limit: int = DEFAULT_BULK_LIMIT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Iterator[list[dict[str, Any]]]:
        """Busca páginas bulk-data; retorna blocos (compatível com sienge_sync)."""
        offset = 0
        seen_first_keys: set[str | int] = set()

        while True:
            separator = "&" if "?" in url else "?"
            paged_url = f"{url}{separator}limit={limit}&offset={offset}"

            try:
                data = self.get_json(paged_url, timeout=timeout, retries=1)
                if not data:
                    break

                page_results = data.get("data", data.get("results", []))
                if not page_results:
                    break

                first_item = page_results[0]
                first_key = first_item.get("id") or f"{first_item.get('billId')}-{first_item.get('installmentId')}"
                if first_key in seen_first_keys:
                    break
                seen_first_keys.add(first_key)

                yield page_results

                if len(page_results) < limit:
                    break
                offset += limit
            except Exception as e:
                print(f"[Sienge Sync] Exception na URL {paged_url}: {str(e)}")
                break

    def paginate_v1_collect(
        self,
        url: str,
        *,
        limit: int = DEFAULT_V1_LIMIT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> list[dict[str, Any]]:
        """Busca todas as páginas da API v1 (compatível com sienge_api)."""
        offset = 0
        all_results: list[dict[str, Any]] = []

        while True:
            separator = "&" if "?" in url else "?"
            paged_url = f"{url}{separator}limit={limit}&offset={offset}"

            try:
                data = self.get_json(paged_url, timeout=timeout, retries=1)
                if not data:
                    break

                page_results = data.get("results", [])
                if not page_results:
                    break

                all_results.extend(page_results)

                metadata = data.get("resultSetMetadata", {})
                count = metadata.get("count", 0)
                if count < limit:
                    break
                offset += limit
            except urllib.error.URLError as e:
                print(f"[Sienge API] Exception ao acessar {paged_url}: {e}")
                break

        return all_results

    def paginate_v1_pages(
        self,
        url: str,
        *,
        limit: int = DEFAULT_V1_LIMIT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Generator[list[dict[str, Any]], None, None]:
        """Paginação v1 por blocos (units, etc.)."""
        offset = 0
        while True:
            separator = "&" if "?" in url else "?"
            paged_url = f"{url}{separator}limit={limit}&offset={offset}"

            data = self.get_json(paged_url, timeout=timeout, retries=1)
            if not data:
                break

            results = data.get("results", [])
            if not results:
                break

            yield results

            metadata = data.get("resultSetMetadata", {})
            count = metadata.get("count", len(results))
            if count < limit or len(results) < limit:
                break
            offset += limit

    @staticmethod
    def auth_string_from_user_pass(user: str, password: str) -> str:
        return f"{user}:{password}"

    @classmethod
    def from_auth_string(cls, subdomain: str, auth_string: str) -> "SiengeClient":
        user, _, password = auth_string.partition(":")
        return cls(subdomain=subdomain, user=user, password=password)
