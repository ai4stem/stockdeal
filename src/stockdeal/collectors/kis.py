"""KIS (한국투자증권) OpenAPI client.

Covers:
- OAuth token issuance / refresh with on-disk caching
- REST: quotes, daily bars, investor net buying, account balance, orders
- WebSocket: real-time trade stream (H0STCNT0) for watchlist tickers (skeleton)

Docs: https://apiportal.koreainvestment.com/
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from stockdeal.config import KISEnv, get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)

PROD_BASE = "https://openapi.koreainvestment.com:9443"
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
PROD_WS = "ws://ops.koreainvestment.com:21000"
PAPER_WS = "ws://ops.koreainvestment.com:31000"

TOKEN_CACHE_PATH = Path(".kis_token.json")


@dataclass
class KISToken:
    access_token: str
    expires_at: datetime  # UTC

    def is_valid(self, safety_margin_sec: int = 120) -> bool:
        return datetime.now(timezone.utc) + timedelta(seconds=safety_margin_sec) < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {"access_token": self.access_token, "expires_at": self.expires_at.isoformat()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KISToken":
        return cls(
            access_token=data["access_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )


class KISError(RuntimeError):
    pass


class KISClient:
    """Async KIS REST client. One instance per process is fine."""

    def __init__(self, token_cache_path: Path | None = None) -> None:
        s = get_settings()
        self._settings = s
        self.base_url = PROD_BASE if s.kis_env is KISEnv.PROD else PAPER_BASE
        self.ws_url = PROD_WS if s.kis_env is KISEnv.PROD else PAPER_WS
        self._token: KISToken | None = None
        self._token_path = token_cache_path or TOKEN_CACHE_PATH
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    async def get_access_token(self) -> str:
        if self._token and self._token.is_valid():
            return self._token.access_token

        if self._token is None and self._token_path.exists():
            try:
                cached = KISToken.from_dict(json.loads(self._token_path.read_text()))
                if cached.is_valid():
                    self._token = cached
                    return cached.access_token
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                log.warning("kis_token_cache_unreadable", error=str(exc))

        return await self._issue_token()

    async def _issue_token(self) -> str:
        s = self._settings
        payload = {
            "grant_type": "client_credentials",
            "appkey": s.kis_app_key.get_secret_value(),
            "appsecret": s.kis_app_secret.get_secret_value(),
        }
        r = await self._http.post("/oauth2/tokenP", json=payload)
        if r.status_code != 200:
            raise KISError(f"token issue failed: {r.status_code} {r.text}")
        body = r.json()
        access_token = body["access_token"]
        # KIS returns expires_in (seconds) and access_token_token_expired (datetime str)
        expires_in = int(body.get("expires_in", 86400))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._token = KISToken(access_token=access_token, expires_at=expires_at)
        try:
            self._token_path.write_text(json.dumps(self._token.to_dict()))
        except OSError as exc:
            log.warning("kis_token_cache_write_failed", error=str(exc))
        log.info("kis_token_issued", expires_at=expires_at.isoformat())
        return access_token

    async def _headers(self, tr_id: str) -> dict[str, str]:
        token = await self.get_access_token()
        s = self._settings
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": s.kis_app_key.get_secret_value(),
            "appsecret": s.kis_app_secret.get_secret_value(),
            "tr_id": tr_id,
            "custtype": "P",  # personal
        }

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    async def fetch_current_price(self, ticker: str) -> dict[str, Any]:
        """Return parsed current price snapshot for a KOSPI/KOSDAQ ticker."""
        headers = await self._headers(tr_id="FHKST01010100")
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
        r = await self._http.get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            params=params,
            headers=headers,
        )
        body = self._unwrap(r)
        out = body["output"]
        return {
            "ticker": ticker,
            "price": int(out["stck_prpr"]),
            "open": int(out["stck_oprc"]),
            "high": int(out["stck_hgpr"]),
            "low": int(out["stck_lwpr"]),
            "prev_close": int(out["stck_sdpr"]),
            "change": int(out["prdy_vrss"]),
            "change_pct": float(out["prdy_ctrt"]),
            "volume": int(out["acml_vol"]),
            "trade_value": int(out["acml_tr_pbmn"]),
            "name": out.get("hts_kor_isnm"),
            "raw": out,
        }

    async def fetch_daily_bars(
        self,
        ticker: str,
        end_date: date | None = None,
        days: int = 100,
        adjusted: bool = True,
    ) -> list[dict[str, Any]]:
        """Daily OHLCV bars for the past `days` calendar days ending at end_date.

        Note: KIS endpoint caps response length (~100 bars); for longer
        histories chain calls by sliding the date window.
        """
        end_date = end_date or date.today()
        start_date = end_date - timedelta(days=days)
        headers = await self._headers(tr_id="FHKST03010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
        }
        r = await self._http.get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            params=params,
            headers=headers,
        )
        body = self._unwrap(r)
        rows = body.get("output2") or []
        bars: list[dict[str, Any]] = []
        for row in rows:
            d = row.get("stck_bsop_date")
            if not d:
                continue
            bars.append(
                {
                    "ticker": ticker,
                    "trade_date": datetime.strptime(d, "%Y%m%d").date(),
                    "open": int(row["stck_oprc"]),
                    "high": int(row["stck_hgpr"]),
                    "low": int(row["stck_lwpr"]),
                    "close": int(row["stck_clpr"]),
                    "volume": int(row["acml_vol"]),
                    "trade_value": int(row.get("acml_tr_pbmn") or 0),
                }
            )
        bars.sort(key=lambda x: x["trade_date"])
        return bars

    async def fetch_investor_net(self, ticker: str) -> dict[str, Any]:
        # TODO: 외국인/기관 순매수 (inquire-investor)
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Account / orders
    # ------------------------------------------------------------------
    async def fetch_balance(self) -> dict[str, Any]:
        raise NotImplementedError

    async def place_order(
        self,
        ticker: str,
        side: str,
        qty: int,
        price: int | None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def cancel_order(self, kis_order_id: str) -> dict[str, Any]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _unwrap(self, r: httpx.Response) -> dict[str, Any]:
        if r.status_code != 200:
            raise KISError(f"http {r.status_code}: {r.text[:300]}")
        body = r.json()
        rt_cd = body.get("rt_cd")
        if rt_cd not in (None, "0"):
            raise KISError(f"kis rt_cd={rt_cd} msg={body.get('msg1')}")
        return body


class KISWebSocket:
    """Real-time trade stream subscriber (skeleton)."""

    def __init__(self) -> None:
        s = get_settings()
        self.ws_url = PROD_WS if s.kis_env is KISEnv.PROD else PAPER_WS

    async def run(self, tickers: list[str]) -> None:
        # TODO: connect, subscribe H0STCNT0 per ticker, aggregate ticks to 1m bars.
        raise NotImplementedError
