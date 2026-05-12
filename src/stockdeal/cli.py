"""Typer CLI entrypoint.

Commands:
  stockdeal serve         -> run FastAPI + scheduler
  stockdeal worker        -> run real-time worker (KIS WS + DART/news polling)
  stockdeal report        -> build and email today's report (manual trigger)
  stockdeal db-init       -> apply sql/schema.sql against MYSQL
  stockdeal kis price     -> fetch current price snapshot for a ticker
  stockdeal kis bars      -> fetch recent daily bars (and optionally upsert to DB)
  stockdeal kis ingest    -> ingest daily bars for the configured watchlist
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich import print as rprint
from rich.table import Table

from stockdeal.config import get_settings
from stockdeal.logging import configure_logging, get_logger

app = typer.Typer(add_completion=False, no_args_is_help=True)
kis_app = typer.Typer(add_completion=False, no_args_is_help=True, help="KIS OpenAPI helpers")
app.add_typer(kis_app, name="kis")
log = get_logger(__name__)


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI service with embedded scheduler."""
    import uvicorn

    configure_logging()
    uvicorn.run("stockdeal.api:app", host=host, port=port, factory=False)


@app.command()
def worker() -> None:
    """Run the real-time data worker."""
    configure_logging()
    log.warning("worker_not_implemented")
    # TODO: wire KISWebSocket + DART poller + news poller event loop.


@app.command()
def report() -> None:
    """Build and email today's daily report."""
    from datetime import date

    from stockdeal.reports.daily import send_daily

    configure_logging()
    send_daily(date.today())


@app.command(name="db-init")
def db_init(schema: Path = Path("sql/schema.sql")) -> None:
    """Apply the schema DDL to MySQL using the configured connection."""
    import pymysql

    s = get_settings()
    configure_logging()
    ddl = schema.read_text(encoding="utf-8")
    # CREATE DATABASE in the script targets `stockdeal`; connect server-level.
    conn = pymysql.connect(
        host=s.db_host,
        port=s.db_port,
        user=s.db_user,
        password=s.db_password.get_secret_value(),
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            for stmt in _split_sql(ddl):
                if stmt.strip():
                    cur.execute(stmt)
        conn.commit()
        log.info("db_init_done")
    finally:
        conn.close()


def _split_sql(text: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.strip().endswith(";"):
            out.append("\n".join(buf))
            buf = []
    if buf:
        out.append("\n".join(buf))
    return out


@kis_app.command("price")
def kis_price(ticker: str) -> None:
    """Print a current price snapshot for TICKER."""
    from stockdeal.collectors.kis import KISClient

    configure_logging()

    async def _run() -> dict:
        client = KISClient()
        try:
            return await client.fetch_current_price(ticker)
        finally:
            await client.aclose()

    snap = asyncio.run(_run())
    snap.pop("raw", None)
    rprint(snap)


@kis_app.command("bars")
def kis_bars(
    ticker: str,
    days: int = typer.Option(60, help="Calendar days of history to request"),
    save: bool = typer.Option(False, help="Upsert results into bar_daily"),
) -> None:
    """Fetch daily OHLCV bars for TICKER; optionally save to MySQL."""
    from stockdeal.collectors.kis import KISClient
    from stockdeal.db.repositories import upsert_daily_bars

    configure_logging()

    async def _run() -> list[dict]:
        client = KISClient()
        try:
            return await client.fetch_daily_bars(ticker, days=days)
        finally:
            await client.aclose()

    bars = asyncio.run(_run())

    table = Table(title=f"{ticker} — last {len(bars)} daily bars")
    for col in ("date", "open", "high", "low", "close", "volume"):
        table.add_column(col, justify="right")
    for b in bars[-min(20, len(bars)):]:
        table.add_row(
            b["trade_date"].isoformat(),
            f"{b['open']:,}",
            f"{b['high']:,}",
            f"{b['low']:,}",
            f"{b['close']:,}",
            f"{b['volume']:,}",
        )
    rprint(table)

    if save:
        n = upsert_daily_bars(bars)
        log.info("bar_daily_upserted", ticker=ticker, rows=n)


@kis_app.command("ingest")
def kis_ingest(days: int = typer.Option(60, help="History window per ticker")) -> None:
    """Ingest daily bars for every ticker in WATCHLIST."""
    from stockdeal.collectors.kis import KISClient
    from stockdeal.db.repositories import upsert_daily_bars

    configure_logging()
    s = get_settings()

    async def _run() -> dict[str, int]:
        client = KISClient()
        results: dict[str, int] = {}
        try:
            for ticker in s.watchlist_tickers:
                bars = await client.fetch_daily_bars(ticker, days=days)
                results[ticker] = upsert_daily_bars(bars)
                log.info("ingest_daily", ticker=ticker, rows=results[ticker])
        finally:
            await client.aclose()
        return results

    summary = asyncio.run(_run())
    rprint(json.dumps(summary, indent=2))


if __name__ == "__main__":
    app()
