"""RSS feed poller for free headline sources.

Sources to subscribe (initial set):
- Reuters: business / technology
- CNBC: top news / technology
- SemiWiki main feed
- DIGITIMES
- 연합뉴스, 전자신문 (국내)

Bodies must be fetched separately (respect robots.txt).
"""
from __future__ import annotations

from dataclasses import dataclass

import feedparser

from stockdeal.collectors.news.base import NewsItem


@dataclass
class RssSource:
    name: str
    url: str
    language: str = "en"


DEFAULT_SOURCES: list[RssSource] = [
    RssSource("reuters_business", "https://feeds.reuters.com/reuters/businessNews"),
    RssSource("cnbc_top", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    RssSource("semiwiki", "https://semiwiki.com/feed/"),
    RssSource("yna_economy", "https://www.yna.co.kr/rss/economy.xml", language="ko"),
    RssSource("etnews", "https://rss.etnews.com/Section902.xml", language="ko"),
]


class RssPoller:
    def __init__(self, sources: list[RssSource] | None = None) -> None:
        self.sources = sources or DEFAULT_SOURCES

    def poll_all(self) -> list[NewsItem]:
        # TODO: feedparser.parse() each source; convert to NewsItem; dedupe by url_hash upstream.
        raise NotImplementedError
