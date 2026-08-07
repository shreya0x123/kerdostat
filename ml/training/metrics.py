"""
Kerdostat ML Training — Evaluation Metrics
===========================================
Pure-NumPy metric functions for price-forecast evaluation.

All metrics operate in RAW DOLLAR SPACE (after inverse-transforming
LSTM predictions). Results are interpretable and unit-consistent.

Metrics provided:
    - MAE   (Mean Absolute Error in $)
    - RMSE  (Root Mean Squared Error in $)
    - MAPE  (Mean Absolute Percentage Error in %)
    - Directional Accuracy (fraction of correct up/down forecasts)

Usage:
    from ml.training.metrics import compute_metrics, directional_accuracy

    results = compute_metrics(y_true, y_pred)
    da = directional_accuracy(y_true, y_pred)
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Optional


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:
    """
    Compute MAE, RMSE, and MAPE between true and predicted prices.

    Args:
        y_true: Ground-truth Close prices (1-D array, raw $ space).
        y_pred: Predicted Close prices (1-D array, same length).

    Returns:
        dict with keys: mae, rmse, mape, n_samples
    """
    y_true = np.asarray(y_true, dtype=np.float64).flatten()
    y_pred = np.asarray(y_pred, dtype=np.float64).flatten()

    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Shape mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}"
        )
    if len(y_true) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    errors     = y_true - y_pred
    abs_errors = np.abs(errors)

    mae  = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MAPE: skip zero-valued actuals to avoid divide-by-zero
    nonzero = y_true != 0
    if nonzero.any():
        mape = float(
            np.mean(abs_errors[nonzero] / np.abs(y_true[nonzero])) * 100
        )
    else:
        mape = float("nan")

    return {
        "mae":       round(mae,  4),
        "rmse":      round(rmse, 4),
        "mape":      round(mape, 4),
        "n_samples": int(len(y_true)),
    }


def directional_accuracy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Optional[float]:
    """
    Fraction of test steps where the model correctly predicted the direction
    of price movement (up vs down).

    Definition:
        actual_direction[i]    = sign(y_true[i] - y_true[i-1])
        predicted_direction[i] = sign(y_pred[i] - y_true[i-1])
        DA = mean(actual_direction == predicted_direction)

    Using y_true[i-1] as the "known current price" from which direction
    is measured — this correctly simulates live trading conditions where
    today's price is known and we want to know if tomorrow's move is up or down.

    Args:
        y_true: 1-D array of ground-truth prices (length N).
        y_pred: 1-D array of predicted prices (length N).

    Returns:
        Directional accuracy in [0, 1], or None if fewer than 2 samples.
    """
    y_true = np.asarray(y_true, dtype=np.float64).flatten()
    y_pred = np.asarray(y_pred, dtype=np.float64).flatten()

    if len(y_true) < 2:
        return None

    # Actual direction: did price go up from i-1 to i?
    actual_dir = np.diff(y_true) > 0                 # shape (N-1,)

    # Predicted direction: is y_pred[i] > y_true[i-1]?
    pred_dir = y_pred[1:] > y_true[:-1]              # shape (N-1,)

    return float(np.mean(actual_dir == pred_dir))


def beats_baseline(
    baseline_metrics: Dict[str, float],
    model_metrics: Dict[str, float],
    metric: str = "rmse",
) -> bool:
    """Return True if model metric is strictly better (lower) than baseline."""
    return model_metrics[metric] < baseline_metrics[metric]


def format_comparison_report(
    model_name: str,
    baseline_metrics: Dict[str, float],
    model_metrics: Dict[str, float],
    da: Optional[float] = None,
) -> str:
    """
    Return a formatted text report comparing model vs naive baseline.

    Args:
        model_name:       e.g. "LSTM"
        baseline_metrics: from NaiveBaseline.compute_metrics()
        model_metrics:    from compute_metrics()
        da:               directional accuracy [0, 1] or None

    Returns:
        Multi-line string report.
    """
    def pct_diff(base, val):
        if base == 0:
            return "N/A"
        diff = (base - val) / base * 100
        arrow = "↓" if diff > 0 else "↑"
        return f"{arrow} {abs(diff):.1f}%"

    lines = [
        "=" * 60,
        f"  MODEL ACCURACY REPORT — {model_name} vs Naive Baseline",
        "=" * 60,
        f"  {'Metric':<10} {'Baseline':>12} {'Model':>12} {'vs Baseline':>14}",
        "  " + "-" * 56,
        f"  {'MAE ($)':<10} {baseline_metrics['mae']:>12.4f} "
        f"{model_metrics['mae']:>12.4f} {pct_vs(baseline_metrics['mae'], model_metrics['mae']):>14}",
        f"  {'RMSE ($)':<10} {baseline_metrics['rmse']:>12.4f} "
        f"{model_metrics['rmse']:>12.4f} {pct_vs(baseline_metrics['rmse'], model_metrics['rmse']):>14}",
        f"  {'MAPE (%)':<10} {baseline_metrics['mape']:>12.4f} "
        f"{model_metrics['mape']:>12.4f} {pct_vs(baseline_metrics['mape'], model_metrics['mape']):>14}",
    ]
    if da is not None:
        lines.append(f"  {'Dir. Acc.':<10} {'N/A':>12} {da*100:>11.1f}% {'':>14}")

    verdict = "BEATS" if beats_baseline(baseline_metrics, model_metrics) else "DOES NOT BEAT"
    lines += [
        "  " + "-" * 56,
        f"  VERDICT: {model_name} {verdict} the naive baseline on RMSE.",
        "=" * 60,
    ]
    return "\n".join(lines)


def pct_vs(baseline: float, model: float) -> str:
    """Formatted percentage improvement string."""
    if baseline == 0:
        return "N/A"
    diff = (baseline - model) / baseline * 100
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.1f}%"
