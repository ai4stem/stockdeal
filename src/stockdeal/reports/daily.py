"""Daily report builder.

Triggered by scheduler at DAILY_REPORT_HOUR (default 22:00 KST). Sections:
1. Market summary (KOSPI/KOSDAQ + US close + FX)
2. Watchlist daily snapshot (OHLCV, foreign/inst, TA)
3. Fundamentals & disclosures of the day
4. Macro highlights
5. Top news (importance >= 4) with Claude commentary
6. Signals & positions (paper vs real comparison)
7. Tomorrow's watch points

Output: HTML via Jinja2 template + plain-text fallback + chart attachments.
Delivered via EmailNotifier; summary line also pushed to Telegram.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stockdeal.notify.email import EmailNotifier

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class DailyReport:
    report_date: date
    sections: dict[str, Any]


def build_report(report_date: date) -> DailyReport:
    # TODO: query DB for each section, return DailyReport.
    raise NotImplementedError


def render_html(report: DailyReport) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("daily.html.j2").render(report=report)


def send_daily(report_date: date) -> None:
    report = build_report(report_date)
    html = render_html(report)
    subject = f"📈 Daily Report {report_date.isoformat()}"
    EmailNotifier().send(subject=subject, html=html)
