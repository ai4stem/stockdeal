"""Technical indicators on daily / minute bars.

Uses pandas_ta. Computed columns are merged onto bar frames and returned;
no DB writes here (separation of concerns).
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def compute_daily_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    """Expect columns: open, high, low, close, volume; index = trade_date."""
    out = bars.copy()
    out["sma20"] = ta.sma(out["close"], length=20)
    out["sma60"] = ta.sma(out["close"], length=60)
    out["sma120"] = ta.sma(out["close"], length=120)
    out["rsi14"] = ta.rsi(out["close"], length=14)
    macd = ta.macd(out["close"])
    if macd is not None:
        out = out.join(macd)
    bb = ta.bbands(out["close"], length=20)
    if bb is not None:
        out = out.join(bb)
    out["atr14"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    return out


def trend_alignment(bars_with_ind: pd.DataFrame) -> str:
    """Return 'up' | 'down' | 'mixed' based on MA stack."""
    last = bars_with_ind.iloc[-1]
    if last["sma20"] > last["sma60"] > last["sma120"]:
        return "up"
    if last["sma20"] < last["sma60"] < last["sma120"]:
        return "down"
    return "mixed"
