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
dart_app = typer.Typer(add_completion=False, no_args_is_help=True, help="Open DART helpers")
llm_app = typer.Typer(add_completion=False, no_args_is_help=True, help="Claude LLM helpers")
app.add_typer(kis_app, name="kis")
app.add_typer(dart_app, name="dart")
app.add_typer(llm_app, name="llm")
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
def report(
    on: str = typer.Option(
        "", help="Report date YYYY-MM-DD (default: today)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Render only; do not send the email"
    ),
    out: Path = typer.Option(
        Path("daily_report.html"), help="Where to write the HTML in --dry-run mode"
    ),
) -> None:
    """Build today's daily report and send via Gmail (or render only with --dry-run)."""
    from datetime import date as _date, datetime as _dt

    from stockdeal.reports.daily import (
        build_report,
        render_html,
        render_plain_text,
        render_subject,
        send_daily,
    )

    configure_logging()
    target = _dt.strptime(on, "%Y-%m-%d").date() if on else _date.today()

    if dry_run:
        report_obj = build_report(target)
        html = render_html(report_obj)
        text = render_plain_text(report_obj)
        out.write_text(html, encoding="utf-8")
        rprint(f"[green]rendered -> {out}[/green]  subject: {render_subject(report_obj)}")
        rprint(text)
        return

    send_daily(target)


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


CORP_CODE_CACHE = Path(".dart_corp_code.json")


def _load_corp_map() -> dict[str, dict]:
    if not CORP_CODE_CACHE.exists():
        raise typer.BadParameter(
            "DART corp_code cache missing. Run `stockdeal dart bootstrap` first."
        )
    return json.loads(CORP_CODE_CACHE.read_text())


@dart_app.command("bootstrap")
def dart_bootstrap(
    update_watchlist: bool = typer.Option(
        True, help="Also write corp_code into ticker rows for the watchlist"
    ),
) -> None:
    """Download DART corp_code mapping and cache it locally."""
    from stockdeal.collectors.dart import DartClient
    from stockdeal.db.repositories import set_ticker_corp_code, upsert_ticker

    configure_logging()
    s = get_settings()

    async def _run() -> list[dict]:
        client = DartClient()
        try:
            zip_bytes = await client.fetch_corp_code_zip()
        finally:
            await client.aclose()
        return DartClient.parse_corp_code_xml(zip_bytes)

    rows = asyncio.run(_run())
    by_stock = {r["stock_code"]: r for r in rows}
    CORP_CODE_CACHE.write_text(json.dumps(by_stock, ensure_ascii=False))
    rprint(f"[green]cached {len(by_stock)} listed firms -> {CORP_CODE_CACHE}[/green]")

    if update_watchlist:
        for ticker in s.watchlist_tickers:
            info = by_stock.get(ticker)
            if not info:
                rprint(f"[yellow]watchlist ticker {ticker} not found in DART map[/yellow]")
                continue
            affected = set_ticker_corp_code(ticker, info["corp_code"])
            if affected == 0:
                upsert_ticker(
                    ticker=ticker,
                    name=info["corp_name"],
                    market="UNKNOWN",
                    corp_code=info["corp_code"],
                    is_watchlist=True,
                )
            rprint(f"  {ticker} {info['corp_name']} -> corp_code={info['corp_code']}")


@dart_app.command("disclosures")
def dart_disclosures(
    ticker: str,
    days: int = typer.Option(30, help="Look back this many days"),
    save: bool = typer.Option(False, help="Upsert results into the disclosure table"),
) -> None:
    """List recent disclosures for TICKER (uses cached corp_code mapping)."""
    from datetime import date, timedelta

    from stockdeal.collectors.dart import DartClient, disclosure_url, parse_rcept_dt
    from stockdeal.db.repositories import upsert_disclosure

    configure_logging()
    corp_map = _load_corp_map()
    if ticker not in corp_map:
        raise typer.BadParameter(f"ticker {ticker} not in DART corp_code cache")
    corp_code = corp_map[ticker]["corp_code"]
    end = date.today()
    bgn = end - timedelta(days=days)

    async def _run() -> list[dict]:
        client = DartClient()
        try:
            return await client.list_disclosures(corp_code, bgn_de=bgn, end_de=end)
        finally:
            await client.aclose()

    items = asyncio.run(_run())

    table = Table(title=f"{ticker} disclosures ({bgn}~{end}) — {len(items)} rows")
    for col in ("rcept_dt", "report_nm", "rcept_no"):
        table.add_column(col)
    for it in items[:30]:
        table.add_row(it["rcept_dt"], it["report_nm"], it["rcept_no"])
    rprint(table)

    if save:
        saved = 0
        for it in items:
            upsert_disclosure(
                {
                    "rcept_no": it["rcept_no"],
                    "ticker": ticker,
                    "corp_code": corp_code,
                    "filed_at": parse_rcept_dt(it["rcept_dt"]),
                    "report_type": it.get("report_nm"),
                    "title": it.get("report_nm"),
                    "url": disclosure_url(it["rcept_no"]),
                }
            )
            saved += 1
        log.info("disclosure_upserted", ticker=ticker, rows=saved)


@dart_app.command("financials")
def dart_financials(
    ticker: str,
    year: int = typer.Option(..., help="Business year, e.g. 2024"),
    report: str = typer.Option("ANNUAL", help="Q1 | HALF | Q3 | ANNUAL"),
    fs: str = typer.Option("OFS", help="OFS=별도, CFS=연결"),
    save: bool = typer.Option(False, help="Upsert results into company_financial"),
) -> None:
    """Fetch annual / quarterly financials for TICKER."""
    from stockdeal.collectors.dart import (
        REPORT_CODES,
        DartClient,
        period_end_for,
        period_type_for,
    )
    from stockdeal.db.repositories import upsert_company_financials

    configure_logging()
    if report not in REPORT_CODES:
        raise typer.BadParameter(f"report must be one of {list(REPORT_CODES)}")
    reprt_code = REPORT_CODES[report]
    corp_map = _load_corp_map()
    if ticker not in corp_map:
        raise typer.BadParameter(f"ticker {ticker} not in DART corp_code cache")
    corp_code = corp_map[ticker]["corp_code"]

    async def _run() -> list[dict]:
        client = DartClient()
        try:
            return await client.fetch_financial_statements(
                corp_code, bsns_year=year, reprt_code=reprt_code, fs_div=fs
            )
        finally:
            await client.aclose()

    accounts = asyncio.run(_run())

    table = Table(title=f"{ticker} {year} {report} {fs} — {len(accounts)} accounts")
    for col in ("sj_div", "account_nm", "thstrm_amount"):
        table.add_column(col)
    for a in accounts[:30]:
        table.add_row(a.get("sj_div", ""), a.get("account_nm", ""), a.get("thstrm_amount", ""))
    rprint(table)

    if save:
        period_end = period_end_for(reprt_code, year)
        period_type = period_type_for(reprt_code)
        rows = []
        for a in accounts:
            amount = a.get("thstrm_amount", "").replace(",", "").strip()
            try:
                value = float(amount) if amount and amount != "-" else None
            except ValueError:
                value = None
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "period_type": period_type,
                    "account_code": (a.get("account_id") or a.get("account_nm") or "")[:32],
                    "account_name": a.get("account_nm", "")[:128],
                    "value": value,
                    "unit": a.get("currency", "KRW"),
                    "source_rcept_no": a.get("rcept_no"),
                }
            )
        n = upsert_company_financials(rows)
        log.info("financials_upserted", ticker=ticker, rows=n)


@llm_app.command("ask")
def llm_ask(
    prompt: str = typer.Argument(..., help="User prompt"),
    tier: str = typer.Option("fast", help="fast | smart | deep"),
    system: str = typer.Option(
        "You are a concise assistant for a Korean semiconductor stock analysis system.",
        help="System prompt",
    ),
    json_mode: bool = typer.Option(False, help="Force JSON output"),
    max_tokens: int = typer.Option(1024),
) -> None:
    """Send a single prompt to Claude at the chosen tier and print the result."""
    from stockdeal.analysis.llm import ClaudeClient, Tier

    configure_logging()
    client = ClaudeClient()
    result = client.ask(
        tier=Tier(tier),
        system=system,
        user=prompt,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )
    rprint("[bold]model:[/bold]", result.model)
    rprint("[bold]usage:[/bold]", result.usage)
    rprint("[bold]stop:[/bold]", result.stop_reason)
    if json_mode and result.parsed is not None:
        rprint("[bold]parsed:[/bold]")
        rprint(result.parsed)
    rprint("[bold]text:[/bold]")
    rprint(result.text)


@llm_app.command("test")
def llm_test() -> None:
    """Smoke-test all three tiers with a trivial prompt."""
    from stockdeal.analysis.llm import ClaudeClient, Tier

    configure_logging()
    client = ClaudeClient()
    for tier in (Tier.FAST, Tier.SMART, Tier.DEEP):
        result = client.ask(
            tier=tier,
            system="Respond with the single word PONG.",
            user="ping",
            max_tokens=16,
            cache_system=False,
        )
        rprint(
            f"[green]{tier.value}[/green] {result.model} -> "
            f"{result.text!r} (in={result.usage['input_tokens']} out={result.usage['output_tokens']})"
        )


if __name__ == "__main__":
    app()
