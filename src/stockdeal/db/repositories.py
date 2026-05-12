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


def set_ticker_corp_code(ticker: str, corp_code: str) -> int:
    """Update corp_code on an existing ticker row. Returns rows affected."""
    sql = text(
        "UPDATE ticker SET corp_code = :corp_code WHERE ticker = :ticker"
    )
    with get_session() as session:
        result = session.execute(sql, {"ticker": ticker, "corp_code": corp_code})
        return result.rowcount or 0


def upsert_disclosure(row: dict) -> None:
    """Upsert a single disclosure record (no summary/importance yet)."""
    sql = text(
        """
        INSERT INTO disclosure
            (rcept_no, ticker, corp_code, filed_at, report_type, title, url)
        VALUES
            (:rcept_no, :ticker, :corp_code, :filed_at, :report_type, :title, :url)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            report_type = VALUES(report_type),
            url = VALUES(url)
        """
    )
    with get_session() as session:
        session.execute(sql, row)


def upsert_company_financials(rows: Iterable[dict]) -> int:
    sql = text(
        """
        INSERT INTO company_financial
            (ticker, period_end, period_type, account_code, account_name, value, unit, source_rcept_no)
        VALUES
            (:ticker, :period_end, :period_type, :account_code, :account_name, :value, :unit, :source_rcept_no)
        ON DUPLICATE KEY UPDATE
            account_name = VALUES(account_name),
            value = VALUES(value),
            unit = VALUES(unit),
            source_rcept_no = VALUES(source_rcept_no)
        """
    )
    rows_list = list(rows)
    if not rows_list:
        return 0
    with get_session() as session:
        session.execute(sql, rows_list)
    return len(rows_list)


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
