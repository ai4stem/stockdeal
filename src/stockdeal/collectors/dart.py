"""Open DART API client.

Docs: https://opendart.fss.or.kr/

Endpoints used:
- list.json           : disclosure list (poll every 10~30s for watchlist corp_codes)
- document.xml/zip    : raw filing body
- fnlttSinglAcntAll   : single-company financial statements (annual/quarterly)
- corpCode.xml        : corp_code mapping (bootstrap once)
"""
from __future__ import annotations

import httpx

from stockdeal.config import get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)

BASE = "https://opendart.fss.or.kr/api"


class DartClient:
    def __init__(self) -> None:
        self._key = get_settings().dart_api_key.get_secret_value()
        self._http = httpx.AsyncClient(base_url=BASE, timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_disclosures(
        self,
        corp_code: str | None = None,
        bgn_de: str | None = None,
        end_de: str | None = None,
        page_no: int = 1,
        page_count: int = 100,
    ) -> dict:
        # TODO: GET /list.json
        raise NotImplementedError

    async def fetch_corp_code_map(self) -> bytes:
        # TODO: GET /corpCode.xml (zip), unzip, parse to {ticker: corp_code}.
        raise NotImplementedError

    async def fetch_financial_statements(
        self,
        corp_code: str,
        bsns_year: int,
        reprt_code: str,           # 11011 사업, 11012 반기, 11013 1Q, 11014 3Q
    ) -> dict:
        # TODO: GET /fnlttSinglAcntAll.json
        raise NotImplementedError

    async def fetch_document(self, rcept_no: str) -> bytes:
        # TODO: GET /document.xml -> zip -> XML body
        raise NotImplementedError
