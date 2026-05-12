"""Runtime trading-mode mutation.

The mode lives in settings (env-loaded default) but can be overridden at
runtime via API / Telegram. Every change is journaled into
`trading_mode_history`.
"""
from __future__ import annotations

from stockdeal.config import TradingMode, get_settings


def set_mode(new_mode: TradingMode, changed_by: str, reason: str | None = None) -> None:
    # TODO: write trading_mode_history row; flip settings.trading_mode in process.
    s = get_settings()
    s.trading_mode = new_mode


def get_mode() -> TradingMode:
    return get_settings().trading_mode


def halt(reason: str = "manual /halt") -> None:
    set_mode(TradingMode.OFF, changed_by="kill_switch", reason=reason)
