"""Risk limit checks applied before every real order.

Checks (all must pass):
- Trading mode is CONFIRM or AUTO (else reject)
- Daily order budget not exceeded (settings.daily_order_budget_ratio * equity)
- Per-ticker position cap (settings.max_position_ratio)
- Cool-down: no re-entry on same ticker within N minutes
- Kill switch not active (see runtime flag)
- ATR-based sanity: requested price within reasonable band of current price

Returns RiskDecision(approved, reasons).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskDecision:
    approved: bool
    reasons: list[str]


def check_order(ticker: str, side: str, qty: int, price: float | None) -> RiskDecision:
    # TODO: implement.
    raise NotImplementedError
