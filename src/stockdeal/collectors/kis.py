"""KIS (한국투자증권) OpenAPI client.

Covers:
- OAuth token issuance / refresh
- REST: quotes, daily bars, investor net buying, account balance, orders
- WebSocket: real-time trade stream (H0STCNT0) for watchlist tickers

Docs: https://apiportal.koreainvestment.com/
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from stockdeal.config import KISEnv, get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)

PROD_BASE = "https://openapi.koreainvestment.com:9443"
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
PROD_WS = "ws://ops.koreainvestment.com:21000"
PAPER_WS = "ws://ops.koreainvestment.com:31000"


@dataclass
class KISToken:
    access_token: str
    expires_at: datetime


class KISClient:
    """Thin wrapper over KIS REST API.

    Token caching: in-memory for now; persist to DB later to survive restarts.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self.base_url = PROD_BASE if settings.kis_env is KISEnv.PROD else PAPER_BASE
        self.ws_url = PROD_WS if settings.kis_env is KISEnv.PROD else PAPER_WS
        self._token: KISToken | None = None
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    async def get_access_token(self) -> str:
        # TODO: POST /oauth2/tokenP, cache until expires_at - 60s.
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    async def fetch_current_price(self, ticker: str) -> dict:
        # TODO: /uapi/domestic-stock/v1/quotations/inquire-price
        raise NotImplementedError

    async def fetch_daily_bars(self, ticker: str, days: int = 100) -> list[dict]:
        # TODO: /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
        raise NotImplementedError

    async def fetch_investor_net(self, ticker: str) -> dict:
        # TODO: 외국인/기관 순매수 - inquire-investor
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Account / orders
    # ------------------------------------------------------------------
    async def fetch_balance(self) -> dict:
        # TODO: /uapi/domestic-stock/v1/trading/inquire-balance
        raise NotImplementedError

    async def place_order(
        self,
        ticker: str,
        side: str,           # "BUY" | "SELL"
        qty: int,
        price: int | None,   # None -> market order
    ) -> dict:
        # TODO: order-cash endpoint with proper tr_id by side and env
        raise NotImplementedError

    async def cancel_order(self, kis_order_id: str) -> dict:
        # TODO: order-rvsecncl
        raise NotImplementedError


class KISWebSocket:
    """Real-time trade stream subscriber.

    For each watchlist ticker subscribe to H0STCNT0; buffer ticks in memory
    and flush 1-minute aggregates to bar_1m.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.ws_url = PROD_WS if settings.kis_env is KISEnv.PROD else PAPER_WS

    async def run(self, tickers: list[str]) -> None:
        # TODO: connect, send subscribe messages, loop recv, parse, dispatch.
        raise NotImplementedError
