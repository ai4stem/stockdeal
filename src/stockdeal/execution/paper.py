"""Paper trading executor.

Fill model:
- Market order: fill at next 1-minute open + slippage (default 10bp)
- Limit order:  fill iff limit >= next minute's low (buy) / <= high (sell)
- Volume cap:   max(fill_qty) = 10% of that minute's traded volume
- Costs:        broker commission per KIS rate + 0.18% transaction tax on SELL
"""
from __future__ import annotations

from decimal import Decimal

from stockdeal.strategy.signal import Signal


DEFAULT_SLIPPAGE_BPS = Decimal("0.001")        # 0.10%
TRANSACTION_TAX = Decimal("0.0018")
COMMISSION_RATE = Decimal("0.00015")           # placeholder; refine per KIS contract


class PaperExecutor:
    async def execute(self, signal: Signal) -> None:
        # TODO: pull next minute bar, decide fill, write trade_paper + update position.
        raise NotImplementedError
