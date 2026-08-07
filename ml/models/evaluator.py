"""
Kerdostat ML Models — Evaluator
=================================
Computes regression evaluation metrics and generates visualisations
comparing actual vs. predicted closing prices.

Metrics:
    MAE  — Mean Absolute Error ($)
    RMSE — Root Mean Squared Error ($)
    MAPE — Mean Absolute Percentage Error (%)

All metrics are computed in raw dollar space (after inverse-transforming
model predictions from scaled [0,1] space). This makes them directly
interpretable: "The model is off by $X on average."

Visualisation:
    A matplotlib line chart is saved to artifacts/plots/
    showing actual (blue) vs. predicted (orange) prices over the test set.

Usage:
    from ml.models.evaluator import ModelEvaluator

    evaluator = ModelEvaluator(config, normalizer)
    metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
    print(metrics)   # {"mae": 1.23, "rmse": 1.87, "mape": 0.72}
    evaluator.plot(bundle.y_test, metrics["predictions"])
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Optional, TYPE_CHECKING

import numpy as np
import matplotlib
matplotlib.use("Agg")   # Non-interactive backend — safe for all environments
import matplotlib.pyplot as plt

from ml.data_pipeline.config import PipelineConfig
from ml.data_pipeline.normalizer import Normalizer

if TYPE_CHECKING:
    from tensorflow import keras  # Only imported for type hints, not at runtime

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Structured evaluation result."""
    mae:  float     # Mean Absolute Error ($)
    rmse: float     # Root Mean Squared Error ($)
    mape: float     # Mean Absolute Percentage Error (%)
    predictions: list[float]    # Model predictions in raw price space
    actuals:     list[float]    # Ground-truth prices from test set

    def summary(self) -> str:
        return (
            f"Evaluation | MAE=${self.mae:.4f} | "
            f"RMSE=${self.rmse:.4f} | MAPE={self.mape:.4f}%"
        )

    def to_dict(self) -> dict:
        """JSON-serialisable dict (predictions/actuals as lists)."""
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "n_samples": len(self.predictions),
        }


class ModelEvaluator:
    """
    Evaluates a trained LSTM model on the test set.

    Requires a fitted Normalizer to inverse-transform model outputs
    from scaled [0,1] space back to real dollar prices.
    """

    def __init__(self, config: PipelineConfig, normalizer: Normalizer) -> None:
        self.config = config
        self.normalizer = normalizer

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> "EvaluationMetrics":
        """
        Run inference on X_test, inverse-transform, and compute metrics.

        Args:
            model:  Trained Keras model.
            X_test: Shape (n, seq_len, n_features) — scaled.
            y_test: Shape (n,) — raw dollar Close prices (ground truth).

        Returns:
            EvaluationMetrics with MAE, RMSE, MAPE, and raw predictions.
        """
        # Inference — output is in scaled [0, 1] space
        scaled_preds = model.predict(X_test, verbose=0).flatten()

        # Inverse-transform to dollar space
        raw_preds = self.normalizer.inverse_transform_close(scaled_preds)

        # Compute metrics in dollar space
        mae  = self._mae(y_test, raw_preds)
        rmse = self._rmse(y_test, raw_preds)
        mape = self._mape(y_test, raw_preds)

        metrics = EvaluationMetrics(
            mae=float(mae),
            rmse=float(rmse),
            mape=float(mape),
            predictions=raw_preds.tolist(),
            actuals=y_test.tolist(),
        )

        logger.info(metrics.summary())
        return metrics

    def save_metrics(
        self,
        metrics: EvaluationMetrics,
        path: Optional[str] = None,
    ) -> str:
        """Save metrics to a JSON file in artifacts/results/."""
        results_dir = os.path.join(self.config.artifacts_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        default_name = (
            f"metrics_{self.config.symbol}_{self.config.candle_interval}.json"
        )
        save_path = path or os.path.join(results_dir, default_name)

        with open(save_path, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
        logger.info("Metrics saved → %s", save_path)
        return save_path

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------
    def plot(
        self,
        actuals: np.ndarray,
        predictions: np.ndarray,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
        show: bool = False,
    ) -> str:
        """
        Plot actual vs. predicted closing prices and save to disk.

        Args:
            actuals:     Ground-truth prices (raw $).
            predictions: Model predictions (raw $).
            title:       Plot title override.
            save_path:   Override default output path.
            show:        If True, call plt.show() (use in notebooks only).

        Returns:
            Absolute path to the saved PNG.
        """
        plots_dir = os.path.join(self.config.artifacts_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        default_name = (
            f"pred_{self.config.symbol}_{self.config.candle_interval}.png"
        )
        out_path = save_path or os.path.join(plots_dir, default_name)

        fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})

        # --- Top: Price comparison ---
        ax1 = axes[0]
        ax1.plot(actuals,     label="Actual Close",    color="#2196F3", linewidth=1.5)
        ax1.plot(predictions, label="Predicted Close", color="#FF9800", linewidth=1.5,
                 linestyle="--")
        ax1.set_ylabel("Price ($)", fontsize=11)
        ax1.set_title(
            title or f"LSTM Price Forecast — {self.config.symbol} ({self.config.candle_interval})",
            fontsize=13, fontweight="bold",
        )
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)

        # --- Bottom: Residuals ---
        ax2 = axes[1]
        residuals = np.asarray(predictions) - np.asarray(actuals)
        ax2.bar(range(len(residuals)), residuals, color="#9E9E9E", alpha=0.6, width=0.8)
        ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax2.set_ylabel("Residual ($)", fontsize=11)
        ax2.set_xlabel("Test Sample Index", fontsize=11)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

        logger.info("Plot saved → %s", out_path)
        return out_path

    # ------------------------------------------------------------------
    # Metric calculations
    # ------------------------------------------------------------------
    @staticmethod
    def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.mean(np.abs(y_true - y_pred)))

    @staticmethod
    def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    @staticmethod
    def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """MAPE in percentage. Avoids division by zero for near-zero prices."""
        y_true = np.asarray(y_true, dtype=float)
        mask = y_true != 0
        if not mask.any():
            return 0.0
        return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
