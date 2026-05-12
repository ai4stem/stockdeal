"""Strategy parameter auto-tuning.

Monthly: grid / Bayesian search over key strategy params (e.g. RSI thresholds,
MA windows, stop-loss %, take-profit %, position size) using walk-forward
validation on the past 6~12 months. Winning param set written to
`strategy_params` with source='auto_tuned' and effective_from=now.

Active params are loaded by the signal engine; older rows get effective_to
filled in.
"""
from __future__ import annotations


def run_monthly() -> None:
    # TODO: implement.
    raise NotImplementedError
