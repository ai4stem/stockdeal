"""Typer CLI entrypoint.

Commands:
  stockdeal serve       -> run FastAPI + scheduler
  stockdeal worker      -> run real-time worker (KIS WS + DART/news polling)
  stockdeal report      -> build and email today's report (manual trigger)
  stockdeal db-init     -> apply sql/schema.sql against MYSQL
"""
from __future__ import annotations

from pathlib import Path

import typer

from stockdeal.config import get_settings
from stockdeal.logging import configure_logging, get_logger

app = typer.Typer(add_completion=False, no_args_is_help=True)
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


if __name__ == "__main__":
    app()
