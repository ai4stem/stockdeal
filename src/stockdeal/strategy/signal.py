"""Signal generation.

A `Signal` is a structured recommendation for a (ticker, horizon, action)
backed by a confidence score, a Claude-written rationale, and a snapshot
of the feature vector used.

Sources (combined):
- Lynch score (fundamentals)
- Technical alignment (trend, RSI, BB)
- ML forecast (timeseries.predict)
- News sentiment (recent N hours, importance-weighted)
- Lessons_learned RAG (caveats from past mistakes)

The combiner is a deliberately simple weighted scheme; Claude DEEP tier
makes the final BUY/SELL/HOLD call given the assembled context.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Horizon(str, Enum):
    INTRADAY = "INTRADAY"
    SHORT = "SHORT"      # 5d
    MID = "MID"          # 20d
    LONG = "LONG"        # 60d+


@dataclass
class Signal:
    ticker: str
    ts: datetime
    strategy: str
    action: Action
    confidence: float
    horizon: Horizon
    reasoning_text: str
    features_snapshot: dict[str, Any]
    llm_model: str


def generate_for(ticker: str) -> Signal | None:
    # TODO: collect inputs, ask Claude DEEP, persist to `signal` table, return.
    raise NotImplementedError
