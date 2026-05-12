"""FRED (St. Louis Fed) — free, no key required for public series via fredapi/HTTPS.

We use the public CSV endpoint: https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10
Series to track (initial set):
- DGS10  10Y Treasury yield
- DGS2   2Y Treasury yield
- DXY    via DTWEXBGS (broad dollar)
- T10YIE breakeven inflation
- CPIAUCSL CPI
"""
from __future__ import annotations

import httpx

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

DEFAULT_SERIES = ["DGS10", "DGS2", "DTWEXBGS", "T10YIE", "CPIAUCSL"]


class FredClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def fetch_series(self, series_id: str) -> list[tuple[str, float]]:
        # TODO: GET BASE?id=<series_id>, parse CSV.
        raise NotImplementedError
