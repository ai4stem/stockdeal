from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from datetime import datetime

_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub("", text)).strip()


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

    def to_row(self) -> dict:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "url": self.url,
            "url_hash": self.url_hash,
            "title": self.title[:512],
            "body": self.body,
            "published_at": self.published_at,
            "language": self.language,
        }
