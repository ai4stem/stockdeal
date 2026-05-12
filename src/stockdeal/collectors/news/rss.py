"""RSS feed poller for free headline sources.

Sources to subscribe (initial set):
- Reuters: business
- CNBC: top news
- SemiWiki main feed
- 연합뉴스 경제, 전자신문

Bodies must be fetched separately (respect robots.txt).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

from stockdeal.collectors.news.base import NewsItem, clean_text


@dataclass
class RssSource:
    name: str
    url: str
    language: str = "en"


DEFAULT_SOURCES: list[RssSource] = [
    RssSource("reuters_business", "https://feeds.reuters.com/reuters/businessNews"),
    RssSource(
        "cnbc_top",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    ),
    RssSource("semiwiki", "https://semiwiki.com/feed/"),
    RssSource("yna_economy", "https://www.yna.co.kr/rss/economy.xml", language="ko"),
    RssSource("etnews", "https://rss.etnews.com/Section902.xml", language="ko"),
]


class RssPoller:
    def __init__(self, sources: list[RssSource] | None = None) -> None:
        self.sources = sources or DEFAULT_SOURCES

    def poll_all(self) -> list[NewsItem]:
        out: list[NewsItem] = []
        for src in self.sources:
            parsed = feedparser.parse(src.url)
            for entry in parsed.entries:
                published = _coerce_dt(entry.get("published_parsed"))
                out.append(
                    NewsItem(
                        source=f"rss:{src.name}",
                        external_id=entry.get("id"),
                        url=entry.get("link", ""),
                        title=clean_text(entry.get("title")),
                        body=clean_text(entry.get("summary")),
                        published_at=published,
                        language=src.language,
                    )
                )
        return [x for x in out if x.url]


def _coerce_dt(t: time.struct_time | None) -> datetime | None:
    if not t:
        return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
