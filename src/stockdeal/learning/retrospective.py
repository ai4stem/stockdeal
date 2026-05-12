"""Weekly retrospective driven by Claude DEEP tier.

Sunday 09:00 KST:
  1. Pull all signals + outcomes from the past week (and trailing 30d for context).
  2. Pull paper vs real comparisons.
  3. Ask Claude DEEP for:
        - Hit rate analysis by strategy / horizon / ticker
        - Common failure patterns
        - 1-3 actionable insights (insert into lessons_learned)
        - Any existing lessons to retire (active=0, retired_reason)
  4. Persist insights, send weekly email report.

Lessons are later injected into the system prompt for signal generation
(simple RAG: top-N active lessons by recency + confidence_score).
"""
from __future__ import annotations


def run_weekly() -> None:
    # TODO: implement.
    raise NotImplementedError
