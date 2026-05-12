"""Upsert helpers for core tables (raw SQL to avoid ORM model boilerplate)."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import text

from stockdeal.db.connection import get_session


def upsert_ticker(
    ticker: str,
    name: str,
    market: str,
    sector: str | None = None,
    corp_code: str | None = None,
    is_watchlist: bool = False,
) -> None:
    sql = text(
        """
        INSERT INTO ticker (ticker, name, market, sector, corp_code, is_watchlist)
        VALUES (:ticker, :name, :market, :sector, :corp_code, :is_watchlist)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            market = VALUES(market),
            sector = COALESCE(VALUES(sector), sector),
            corp_code = COALESCE(VALUES(corp_code), corp_code),
            is_watchlist = VALUES(is_watchlist)
        """
    )
    with get_session() as session:
        session.execute(
            sql,
            {
                "ticker": ticker,
                "name": name,
                "market": market,
                "sector": sector,
                "corp_code": corp_code,
                "is_watchlist": 1 if is_watchlist else 0,
            },
        )


def upsert_daily_bars(bars: Iterable[dict]) -> int:
    """Upsert into bar_daily. Returns number of rows passed in."""
    sql = text(
        """
        INSERT INTO bar_daily
            (ticker, trade_date, open, high, low, close, volume, trade_value)
        VALUES
            (:ticker, :trade_date, :open, :high, :low, :close, :volume, :trade_value)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume),
            trade_value = VALUES(trade_value)
        """
    )
    rows = list(bars)
    if not rows:
        return 0
    with get_session() as session:
        session.execute(sql, rows)
    return len(rows)
