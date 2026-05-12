from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsItem:
    source: str
    url: str
    title: str
    body: str | None = None
    external_id: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    tickers_hint: list[str] = field(default_factory=list)

    @property
    def url_hash(self) -> str:
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()
