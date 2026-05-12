"""Time-series forecasting placeholder.

Candidate models:
- PatchTST / TFT / N-BEATS via Nixtla `neuralforecast`
- XGBoost on engineered factor panel (baseline)

Train cadence: weekly (Sunday 10:00 KST) by default; see scheduler.
Artifacts versioned via MLflow; row inserted in `model_registry` and the
`active=1` model is loaded for inference.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Forecast:
    ticker: str
    horizon_days: int
    expected_return: float
    confidence: float
    model_version: str


def train_weekly() -> None:
    # TODO: pull bar_daily + macro + features, fit, evaluate, register.
    raise NotImplementedError


def predict(ticker: str, horizon_days: int = 5) -> Forecast:
    # TODO: load active model, run inference.
    raise NotImplementedError
