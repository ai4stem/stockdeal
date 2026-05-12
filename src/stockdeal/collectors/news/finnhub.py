"""Finnhub news client.

Docs: https://finnhub.io/docs/api/company-news
Free tier: ~60 calls/min, US-focused.
"""
from __future__ import annotations

import httpx

from stockdeal.collectors.news.base import NewsItem
from stockdeal.config import get_settings


class FinnhubClient:
    BASE = "https://finnhub.io/api/v1"

    def __init__(self) -> None:
        self._token = get_settings().finnhub_api_key.get_secret_value()
        self._http = httpx.AsyncClient(base_url=self.BASE, timeout=10.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def company_news(self, symbol: str, _from: str, to: str) -> list[NewsItem]:
        # TODO: GET /company-news?symbol=...&from=...&to=...&token=...
        raise NotImplementedError

    async def market_news(self, category: str = "general") -> list[NewsItem]:
        # TODO: GET /news?category=...&token=...
        raise NotImplementedError
