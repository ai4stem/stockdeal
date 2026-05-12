"""Daily report builder.

Reads what's currently in the DB (bars, disclosures, signals, trades) and
composes an HTML email. Sections without data are rendered as "데이터 없음".

Triggered by scheduler at DAILY_REPORT_HOUR (default 22:00 KST), or manually
via `stockdeal report`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stockdeal.config import get_settings
from stockdeal.db.repositories import (
    get_disclosures_in_range,
    get_latest_bars,
    get_recent_signals,
    get_recent_trades,
)
from stockdeal.logging import get_logger
from stockdeal.notify.email import EmailNotifier

log = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class WatchlistRow:
    ticker: str
    name: str | None
    close: int | None
    change: int | None
    change_pct: float | None
    volume: int | None
    trend_5d_pct: float | None


@dataclass
class DailyReport:
    report_date: date
    watchlist: list[WatchlistRow] = field(default_factory=list)
    disclosures: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    trades_paper: list[dict] = field(default_factory=list)
    trades_real: list[dict] = field(default_factory=list)


def build_report(report_date: date) -> DailyReport:
    s = get_settings()
    tickers = s.watchlist_tickers
    bars_by_ticker = get_latest_bars(tickers, days=14)

    watchlist: list[WatchlistRow] = []
    for ticker in tickers:
        bars = bars_by_ticker.get(ticker, [])
        if not bars:
            watchlist.append(
                WatchlistRow(
                    ticker=ticker,
                    name=None,
                    close=None,
                    change=None,
                    change_pct=None,
                    volume=None,
                    trend_5d_pct=None,
                )
            )
            continue
        last = bars[-1]
        prev = bars[-2] if len(bars) >= 2 else None
        five_back = bars[-6] if len(bars) >= 6 else bars[0]
        change = (last["close"] - prev["close"]) if prev else None
        change_pct = (change / prev["close"] * 100) if prev and prev["close"] else None
        trend_5d = (
            (last["close"] - five_back["close"]) / five_back["close"] * 100
            if five_back["close"]
            else None
        )
        watchlist.append(
            WatchlistRow(
                ticker=ticker,
                name=None,  # filled by template lookup if needed
                close=last["close"],
                change=change,
                change_pct=change_pct,
                volume=last["volume"],
                trend_5d_pct=trend_5d,
            )
        )

    day_start = datetime.combine(report_date, time.min)
    day_end = day_start + timedelta(days=1)
    disclosures = get_disclosures_in_range(day_start, day_end)
    signals = get_recent_signals(day_start)
    trades_paper = get_recent_trades("PAPER", day_start)
    trades_real = get_recent_trades("REAL", day_start)

    return DailyReport(
        report_date=report_date,
        watchlist=watchlist,
        disclosures=disclosures,
        signals=signals,
        trades_paper=trades_paper,
        trades_real=trades_real,
    )


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(report: DailyReport) -> str:
    return _env().get_template("daily.html.j2").render(report=report)


def render_subject(report: DailyReport) -> str:
    movers = [w for w in report.watchlist if w.change_pct is not None]
    biggest: WatchlistRow | None = (
        max(movers, key=lambda w: abs(w.change_pct or 0)) if movers else None
    )
    if biggest and biggest.change_pct is not None:
        arrow = "▲" if biggest.change_pct >= 0 else "▼"
        return (
            f"📈 Daily {report.report_date.isoformat()} — "
            f"{biggest.ticker} {arrow}{abs(biggest.change_pct):.2f}%"
        )
    return f"📈 Daily {report.report_date.isoformat()}"


def render_plain_text(report: DailyReport) -> str:
    lines: list[str] = [f"Daily Report {report.report_date.isoformat()}", ""]
    lines.append("[Watchlist]")
    for w in report.watchlist:
        if w.close is None:
            lines.append(f"  {w.ticker}: no data")
            continue
        lines.append(
            f"  {w.ticker}: close={w.close:,} "
            f"change={w.change_pct:+.2f}% vol={w.volume:,}"
        )
    lines.append("")
    lines.append(f"[Disclosures] {len(report.disclosures)} rows")
    for d in report.disclosures[:10]:
        lines.append(f"  - {d['filed_at']} {d['ticker']} {d['title']}")
    lines.append("")
    lines.append(f"[Signals] {len(report.signals)} | "
                 f"[Trades P/R] {len(report.trades_paper)}/{len(report.trades_real)}")
    return "\n".join(lines)


def send_daily(report_date: date | None = None) -> None:
    report_date = report_date or date.today()
    report = build_report(report_date)
    html = render_html(report)
    text = render_plain_text(report)
    subject = render_subject(report)
    EmailNotifier().send(subject=subject, html=html, text=text)
    log.info("daily_report_sent", date=report_date.isoformat(), subject=subject)
