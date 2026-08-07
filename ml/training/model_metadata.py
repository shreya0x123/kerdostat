"""
Kerdostat ML Training — Model Metadata
=======================================
Structured metadata for every trained LSTM model. Metadata is persisted
as JSON alongside the saved Keras model so that:
  - The inference pipeline can verify model/data compatibility.
  - Evaluation results are auditable and reproducible.
  - Future re-training can detect whether parameters changed.

Usage:
    from ml.training.model_metadata import ModelMetadata

    meta = ModelMetadata(
        symbol="AAPL", candle_interval="1day",
        sequence_length=60, forecast_horizon=1, ...
    )
    meta.set_metrics(mae=1.23, rmse=1.89, mape=0.65, directional_accuracy=0.54)
    meta.set_baseline_metrics(mae=1.45, rmse=2.10, mape=0.78)
    meta.save("artifacts/results/metadata_AAPL_1day.json")

    # Later:
    meta2 = ModelMetadata.load("artifacts/results/metadata_AAPL_1day.json")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """
    Complete metadata record for a trained LSTM model.

    All fields are JSON-serialisable so the record can be saved
    and loaded without any special deserialization logic.
    """
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    model_name: str = "LSTM"
    model_version: str = ""            # Set from timestamp at save time
    symbol: str = "AAPL"
    candle_interval: str = "1day"

    # ------------------------------------------------------------------
    # Architecture
    # ------------------------------------------------------------------
    sequence_length: int = 60
    forecast_horizon: int = 1
    features: List[str] = field(default_factory=list)
    n_features: int = 0

    lstm_units_1: int = 128
    lstm_units_2: int = 64
    dense_units: int = 32
    dropout_rate: float = 0.2

    # ------------------------------------------------------------------
    # Training data
    # ------------------------------------------------------------------
    training_start: str = ""
    training_end: str = ""
    total_rows_original: int = 0
    rows_after_cleaning: int = 0
    rows_after_feature_engineering: int = 0
    training_samples: int = 0
    validation_samples: int = 0
    test_samples: int = 0

    train_ratio: float = 0.70
    val_ratio: float = 0.15

    # ------------------------------------------------------------------
    # Training results
    # ------------------------------------------------------------------
    epochs_trained: int = 0
    best_val_loss: float = float("inf")
    training_completed_at: str = ""

    # ------------------------------------------------------------------
    # Test-set evaluation metrics (raw dollar space)
    # ------------------------------------------------------------------
    metrics: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "mae": None, "rmse": None, "mape": None, "directional_accuracy": None
    })

    # ------------------------------------------------------------------
    # Naive baseline metrics (for comparison)
    # ------------------------------------------------------------------
    baseline_metrics: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "mae": None, "rmse": None, "mape": None
    })

    # ------------------------------------------------------------------
    # Derived verdict
    # ------------------------------------------------------------------
    beats_baseline: Optional[bool] = None
    improvement_pct_rmse: Optional[float] = None

    # ------------------------------------------------------------------
    # Scaler info (for compatibility check at inference)
    # ------------------------------------------------------------------
    scaler_type: str = "minmax"
    scaler_path: str = ""
    model_path: str = ""

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def set_metrics(
        self,
        mae: float,
        rmse: float,
        mape: float,
        directional_accuracy: Optional[float],
    ) -> None:
        """Populate test-set evaluation metrics."""
        self.metrics = {
            "mae":                  round(mae, 4),
            "rmse":                 round(rmse, 4),
            "mape":                 round(mape, 4),
            "directional_accuracy": (
                round(directional_accuracy, 4)
                if directional_accuracy is not None else None
            ),
        }

    def set_baseline_metrics(
        self,
        mae: float,
        rmse: float,
        mape: float,
    ) -> None:
        """Populate naive baseline metrics."""
        self.baseline_metrics = {
            "mae":  round(mae,  4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 4),
        }

    def compute_verdict(self) -> None:
        """Compare LSTM RMSE vs baseline RMSE and set beats_baseline."""
        m_rmse = self.metrics.get("rmse")
        b_rmse = self.baseline_metrics.get("rmse")
        if m_rmse is not None and b_rmse is not None and b_rmse != 0:
            self.beats_baseline = bool(m_rmse < b_rmse)
            self.improvement_pct_rmse = round(
                (b_rmse - m_rmse) / b_rmse * 100, 2
            )

    def stamp_version(self) -> str:
        """Generate and store a version timestamp string."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.model_version = ts
        self.training_completed_at = datetime.now(timezone.utc).isoformat()
        return ts

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Convert to a plain JSON-serialisable dict."""
        d = asdict(self)
        return d

    def save(self, path: Optional[str] = None) -> str:
        """
        Save metadata as JSON.

        Args:
            path: Override default path.

        Returns:
            Absolute path where the file was saved.
        """
        save_path = path or self._default_path()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info("Metadata saved to: %s", save_path)
        return save_path

    @classmethod
    def load(cls, path: str) -> "ModelMetadata":
        """Load metadata from a JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Allow forward compatibility: ignore unknown keys
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def is_compatible_with(
        self,
        symbol: str,
        candle_interval: str,
        features: List[str],
        sequence_length: int,
        forecast_horizon: int,
    ) -> tuple[bool, str]:
        """
        Check if this metadata is compatible with the given inference request.

        Returns (True, "") if compatible, (False, reason) if not.
        """
        checks = [
            (self.symbol == symbol,
             f"Symbol mismatch: model={self.symbol}, request={symbol}"),
            (self.candle_interval == candle_interval,
             f"Interval mismatch: model={self.candle_interval}, request={candle_interval}"),
            (self.sequence_length == sequence_length,
             f"seq_len mismatch: model={self.sequence_length}, request={sequence_length}"),
            (self.forecast_horizon == forecast_horizon,
             f"horizon mismatch: model={self.forecast_horizon}, request={forecast_horizon}"),
            (self.features == features,
             f"Feature list mismatch"),
        ]
        for ok, reason in checks:
            if not ok:
                return False, reason
        return True, ""

    def _default_path(self) -> str:
        """Fallback path in the project artifacts directory."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return os.path.join(
            project_root, "artifacts", "results",
            f"metadata_{self.symbol}_{self.candle_interval}.json",
        )

    def summary(self) -> str:
        """One-line human-readable summary."""
        da = self.metrics.get("directional_accuracy")
        da_str = f"{da*100:.1f}%" if da is not None else "N/A"
        verdict = "BEATS baseline" if self.beats_baseline else (
            "does not beat baseline" if self.beats_baseline is False else "unverified"
        )
        return (
            f"[{self.model_name}] {self.symbol} {self.candle_interval} | "
            f"MAE=${self.metrics.get('mae', 'N/A')} | "
            f"RMSE=${self.metrics.get('rmse', 'N/A')} | "
            f"MAPE={self.metrics.get('mape', 'N/A')}% | "
            f"DA={da_str} | {verdict}"
        )
