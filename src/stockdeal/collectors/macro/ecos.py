"""ECOS (한국은행 경제통계시스템) client.

Docs: https://ecos.bok.or.kr/api/
Free, requires a key (use the open key for now; later move to dedicated env var).
"""
from __future__ import annotations

import httpx

BASE = "https://ecos.bok.or.kr/api"


class EcosClient:
    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self._http = httpx.AsyncClient(base_url=BASE, timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def fetch_series(
        self,
        stat_code: str,
        cycle: str,         # D / M / Q / A
        start: str,
        end: str,
        item_code1: str = "?",
    ) -> list[dict]:
        # TODO: GET /StatisticSearch/{key}/json/kr/1/100/{stat_code}/{cycle}/{start}/{end}/{item_code1}
        raise NotImplementedError
