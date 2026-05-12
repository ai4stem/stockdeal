"""Naver News Search API.

Docs: https://developers.naver.com/docs/serviceapi/search/news/news.md
Quota: 25,000 calls/day on free tier; up to 100 results per call (display).
"""
from __future__ import annotations

from email.utils import parsedate_to_datetime

import httpx

from stockdeal.collectors.news.base import NewsItem, clean_text
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

    async def search(
        self,
        query: str,
        display: int = 30,
        start: int = 1,
        sort: str = "date",
    ) -> list[NewsItem]:
        r = await self._http.get(
            self.BASE,
            params={"query": query, "display": display, "start": start, "sort": sort},
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        out: list[NewsItem] = []
        for it in items:
            try:
                published = parsedate_to_datetime(it.get("pubDate", ""))
            except (TypeError, ValueError):
                published = None
            out.append(
                NewsItem(
                    source="naver",
                    url=it.get("link") or it.get("originallink") or "",
                    title=clean_text(it.get("title")),
                    body=clean_text(it.get("description")),
                    published_at=published,
                    language="ko",
                    tickers_hint=[],
                )
            )
        return [x for x in out if x.url]
