"""FastAPI control plane.

Endpoints (initial):
  GET  /health
  GET  /mode
  POST /mode {mode}
  POST /halt
  POST /confirm/{intent_id}
  POST /reject/{intent_id}
  GET  /signals/recent

Also hosts the APScheduler instance via lifespan; the real-time worker runs
as a separate process (see cli.py `worker` command).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from stockdeal.config import TradingMode, get_settings
from stockdeal.execution.mode import get_mode, halt, set_mode
from stockdeal.logging import configure_logging, get_logger
from stockdeal.scheduler import build_scheduler

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("api_startup", env=get_settings().app_env)
    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        log.info("api_shutdown")


app = FastAPI(title="stockdeal", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/mode")
async def read_mode() -> dict:
    return {"mode": get_mode().value}


@app.post("/mode")
async def write_mode(mode: TradingMode) -> dict:
    set_mode(mode, changed_by="api", reason="POST /mode")
    return {"mode": mode.value}


@app.post("/halt")
async def post_halt() -> dict:
    halt(reason="POST /halt")
    return {"mode": get_mode().value}
