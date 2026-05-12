"""Upsert + read helpers for core tables (raw SQL to avoid ORM model boilerplate)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import bindparam, text

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


def upsert_news_items(rows: Iterable[dict]) -> int:
    """Insert news rows; on duplicate url_hash, leave existing row alone."""
    sql = text(
        """
        INSERT INTO news_raw
            (source, external_id, url, url_hash, title, body, published_at, language)
        VALUES
            (:source, :external_id, :url, :url_hash, :title, :body, :published_at, :language)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            body  = COALESCE(VALUES(body), body),
            published_at = COALESCE(VALUES(published_at), published_at)
        """
    )
    rows_list = list(rows)
    if not rows_list:
        return 0
    with get_session() as session:
        session.execute(sql, rows_list)
    return len(rows_list)


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


# ----------------------------------------------------------------------
# Read helpers (used by the daily report)
# ----------------------------------------------------------------------
def get_latest_bars(tickers: list[str], days: int = 7) -> dict[str, list[dict]]:
    """Return {ticker: [bar, ...]} sorted ascending by trade_date.

    `days` is calendar days; rows naturally skip weekends/holidays.
    """
    if not tickers:
        return {}
    sql = text(
        """
        SELECT ticker, trade_date, open, high, low, close, volume
        FROM bar_daily
        WHERE ticker IN :tickers AND trade_date >= :since
        ORDER BY ticker, trade_date
        """
    ).bindparams(bindparam("tickers", expanding=True))
    since = date.today() - timedelta(days=days * 2)
    out: dict[str, list[dict]] = {t: [] for t in tickers}
    with get_session() as session:
        for row in session.execute(sql, {"tickers": tickers, "since": since}).mappings():
            out[row["ticker"]].append(dict(row))
    return out


def get_disclosures_in_range(start: datetime, end: datetime) -> list[dict]:
    sql = text(
        """
        SELECT d.rcept_no, d.ticker, t.name AS ticker_name, d.filed_at,
               d.report_type, d.title, d.url, d.importance
        FROM disclosure d
        LEFT JOIN ticker t ON t.ticker = d.ticker
        WHERE d.filed_at >= :start AND d.filed_at < :end
        ORDER BY d.filed_at DESC
        """
    )
    with get_session() as session:
        return [dict(r) for r in session.execute(sql, {"start": start, "end": end}).mappings()]


def get_recent_signals(since: datetime, limit: int = 50) -> list[dict]:
    sql = text(
        """
        SELECT signal_id, ticker, ts, strategy, action, confidence, horizon, reasoning_text
        FROM signal
        WHERE ts >= :since
        ORDER BY ts DESC
        LIMIT :limit
        """
    )
    with get_session() as session:
        return [dict(r) for r in session.execute(sql, {"since": since, "limit": limit}).mappings()]


def get_recent_trades(book: str, since: datetime, limit: int = 100) -> list[dict]:
    table = "trade_real" if book.upper() == "REAL" else "trade_paper"
    sql = text(
        f"""
        SELECT signal_id, ticker, side, qty, fill_price, fill_qty, fill_ts, pnl
        FROM {table}
        WHERE fill_ts >= :since
        ORDER BY fill_ts DESC
        LIMIT :limit
        """
    )
    with get_session() as session:
        return [dict(r) for r in session.execute(sql, {"since": since, "limit": limit}).mappings()]
