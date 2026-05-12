"""Finnhub news client.

Docs: https://finnhub.io/docs/api/company-news
Free tier: ~60 calls/min, US-focused.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
        """`_from` / `to` are YYYY-MM-DD strings."""
        r = await self._http.get(
            "/company-news",
            params={"symbol": symbol, "from": _from, "to": to, "token": self._token},
        )
        r.raise_for_status()
        return [self._to_item(row, symbol_hint=symbol) for row in r.json()]

    async def market_news(self, category: str = "general") -> list[NewsItem]:
        r = await self._http.get(
            "/news", params={"category": category, "token": self._token}
        )
        r.raise_for_status()
        return [self._to_item(row) for row in r.json()]

    @staticmethod
    def _to_item(row: dict, symbol_hint: str | None = None) -> NewsItem:
        ts = row.get("datetime") or 0
        published = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None
        return NewsItem(
            source="finnhub",
            external_id=str(row.get("id")) if row.get("id") is not None else None,
            url=row.get("url", ""),
            title=(row.get("headline") or "")[:512],
            body=row.get("summary"),
            published_at=published,
            language="en",
            tickers_hint=[symbol_hint] if symbol_hint else [],
        )
