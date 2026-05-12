"""Post-mortem labeling of past signals.

Daily at 23:00 KST: for every signal older than 5/20/60 days that lacks a
matching `decision_outcome` row, compute realized return vs the action and
write the outcome label.

Outcome label mapping (BUY signals example):
    realized_return > +2%   -> correct
    realized_return < -2%   -> wrong
    otherwise               -> partial
Symmetric for SELL.
"""
from __future__ import annotations


HORIZONS = (5, 20, 60)


def evaluate_pending_outcomes() -> int:
    # TODO: query signals + bars, compute, insert into decision_outcome. Return rows inserted.
    raise NotImplementedError
