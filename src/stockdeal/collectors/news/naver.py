"""Naver News Search API.

Docs: https://developers.naver.com/docs/serviceapi/search/news/news.md
Quota: 25,000 calls/day on free tier.
"""
from __future__ import annotations

import httpx

from stockdeal.collectors.news.base import NewsItem
from stockdeal.config import get_settings


class NaverNewsClient:
    BASE = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self) -> None:
        s = get_settings()
        self._headers = {
            "X-Naver-Client-Id": s.naver_client_id,
            "X-Naver-Client-Secret": s.naver_client_secret.get_secret_value(),
        }
        self._http = httpx.AsyncClient(headers=self._headers, timeout=10.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def search(self, query: str, display: int = 30, sort: str = "date") -> list[NewsItem]:
        # TODO: call BASE with params, map response items to NewsItem.
        raise NotImplementedError
