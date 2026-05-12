"""Trade dispatcher.

Every signal flows through this single entry point. Behavior depends on
the current TradingMode held in settings (mutable at runtime via the
mode-change API or Telegram command — see notify/telegram.py).

    OFF        : record signal only; no paper, no real
    SIMULATION : run paper executor
    CONFIRM    : run paper executor AND request user confirmation; on approval, run real executor
    AUTO       : run paper executor AND real executor immediately (subject to risk limits)

The paper executor always runs whenever the mode is not OFF, so we have a
consistent comparison series for the same signals.
"""
from __future__ import annotations

from stockdeal.config import TradingMode, get_settings
from stockdeal.execution.paper import PaperExecutor
from stockdeal.execution.real import RealExecutor
from stockdeal.strategy.signal import Signal


class Trader:
    def __init__(self) -> None:
        self.paper = PaperExecutor()
        self.real = RealExecutor()

    async def dispatch(self, signal: Signal) -> None:
        mode = get_settings().trading_mode
        if mode is TradingMode.OFF:
            return

        # Paper trading always runs (except OFF).
        await self.paper.execute(signal)

        if mode is TradingMode.SIMULATION:
            return

        if mode is TradingMode.CONFIRM:
            # TODO: create order_intent + send confirmation request via notify.
            return

        if mode is TradingMode.AUTO:
            # TODO: apply risk checks, then real.execute.
            return
