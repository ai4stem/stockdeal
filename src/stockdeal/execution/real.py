"""Real-money executor (KIS).

Path:
  1. risk.check_order() must approve
  2. KISClient.place_order()
  3. Poll order status / listen for fill
  4. Write trade_real and update position(book=REAL)
  5. Emit fill notification (Telegram)
"""
from __future__ import annotations

from stockdeal.strategy.signal import Signal


class RealExecutor:
    async def execute(self, signal: Signal) -> None:
        # TODO: implement.
        raise NotImplementedError
