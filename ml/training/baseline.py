"""
Kerdostat ML Training — Naive Baseline
=======================================
A naive price forecaster that predicts tomorrow's price = today's price
(random-walk baseline, also called the "no-change" forecast).

This is the mandatory academic benchmark. An LSTM model is only useful
if it consistently outperforms this baseline.

Usage:
    from ml.training.baseline import NaiveBaseline

    baseline = NaiveBaseline()
    metrics = baseline.compute_metrics(y_test)
    # {"mae": 1.23, "rmse": 1.89, "mape": 0.65}
"""

from __future__ import annotations

import numpy as np
from typing import Dict


class NaiveBaseline:
    """
    Random-walk (no-change) baseline predictor.

    Prediction rule:
        predicted_price[t] = actual_price[t-1]

    For a test sequence y_test = [p0, p1, ..., pN]:
        predicted = [p0, p1, ..., p(N-1)]
        actual    = [p1, p2, ..., pN]
    """

    def predict(self, y_test: np.ndarray) -> np.ndarray:
        """Return shifted (previous-day) prices as naive predictions."""
        y = np.asarray(y_test, dtype=np.float64).flatten()
        if len(y) < 2:
            raise ValueError(
                f"NaiveBaseline needs at least 2 test samples, got {len(y)}."
            )
        return y[:-1]

    def compute_metrics(self, y_test: np.ndarray) -> Dict[str, float]:
        """Compute MAE, RMSE, MAPE for naive baseline on y_test."""
        y = np.asarray(y_test, dtype=np.float64).flatten()
        if len(y) < 2:
            raise ValueError("At least 2 test samples required for baseline metrics.")

        predicted = y[:-1]
        actual    = y[1:]

        errors     = actual - predicted
        abs_errors = np.abs(errors)

        mae  = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(errors ** 2)))

        nonzero = actual != 0
        mape = float(np.mean(abs_errors[nonzero] / np.abs(actual[nonzero])) * 100)

        return {
            "mae":       round(mae,  4),
            "rmse":      round(rmse, 4),
            "mape":      round(mape, 4),
            "n_samples": int(len(actual)),
        }

    def beats(
        self,
        baseline_metrics: Dict[str, float],
        model_metrics: Dict[str, float],
        metric: str = "rmse",
    ) -> bool:
        """Return True if model metric is lower (better) than baseline."""
        return model_metrics[metric] < baseline_metrics[metric]

    def improvement_pct(
        self,
        baseline_metrics: Dict[str, float],
        model_metrics: Dict[str, float],
        metric: str = "rmse",
    ) -> float:
        """Percentage improvement: (baseline - model) / baseline * 100."""
        bv = baseline_metrics[metric]
        mv = model_metrics[metric]
        if bv == 0:
            return 0.0
        return round((bv - mv) / bv * 100, 2)
