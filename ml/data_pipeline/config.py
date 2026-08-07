"""
Kerdostat ML Data Pipeline — Configuration
==========================================
Centralised, externalisable configuration for the Day 4 data pipeline
and Day 5 LSTM model.

All tunable parameters live here. No magic numbers appear in any other
module. Configuration is passed explicitly as a `PipelineConfig` object
so that tests can override individual fields without side-effects.

Usage:
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig()                        # defaults
    cfg = PipelineConfig(symbol="TSLA", sequence_length=60)
    cfg = PipelineConfig.from_dict({...})         # from a JSON/YAML load
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import List


# ---------------------------------------------------------------------------
# Feature column names produced by the feature engineer.
# Kept here so every downstream module references the same list.
# ---------------------------------------------------------------------------
DEFAULT_FEATURE_COLUMNS: List[str] = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "RSI",
    "EMA_20",
    "MACD_Line",
    "MACD_Signal",
    "MACD_Histogram",
    "BB_Upper",
    "BB_Middle",
    "BB_Lower",
    "BB_Width",       # Upper - Lower (volatility proxy)
]

# The target column the LSTM will predict
TARGET_COLUMN: str = "Close"


@dataclass
class PipelineConfig:
    """
    Full configuration for the ML data pipeline and LSTM model.

    All fields have sensible defaults so callers only need to
    override what they care about.

    Attributes:
        symbol:           Ticker symbol (e.g. "AAPL").
        candle_interval:  Data granularity — maps to Alpaca TimeFrame.
        start_date:       ISO-8601 start date for historical fetch.
        end_date:         ISO-8601 end date for historical fetch.
        sequence_length:  Number of time-steps fed into the LSTM (window size).
        target_horizon:   Number of steps ahead to predict (1 = next candle).
        train_ratio:      Fraction of data used for training.
        val_ratio:        Fraction used for validation.
                          test_ratio = 1 - train_ratio - val_ratio.
        feature_columns:  Ordered list of input feature column names.
        target_column:    Column used as the prediction target.
        scaler_type:      Only "minmax" is supported currently.
        artifacts_dir:    Root directory for all saved artefacts.
        max_fill_gap:     Max consecutive NaNs to forward-fill before dropping.

        # LSTM hyper-parameters
        lstm_units_1:     Units in first LSTM layer.
        lstm_units_2:     Units in second LSTM layer.
        dense_units:      Units in intermediate Dense layer.
        dropout_rate:     Dropout fraction after each LSTM layer.
        learning_rate:    Adam optimiser learning rate.
        batch_size:       Training batch size.
        epochs:           Max training epochs (EarlyStopping may exit earlier).
        early_stopping_patience: Epochs without improvement before stopping.
        reduce_lr_patience:      Epochs before learning-rate reduction.
        reduce_lr_factor:        LR reduction multiplier.
    """
    # --- Data source ---
    symbol: str = "AAPL"
    candle_interval: str = "1day"
    start_date: str = "2020-01-01"
    end_date: str = "2025-01-01"

    # --- Windowing ---
    sequence_length: int = 30
    target_horizon: int = 1

    # --- Split ratios ---
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    # test_ratio is implied: 1 - train_ratio - val_ratio

    # --- Features ---
    feature_columns: List[str] = field(
        default_factory=lambda: list(DEFAULT_FEATURE_COLUMNS)
    )
    target_column: str = TARGET_COLUMN

    # --- Scaling ---
    scaler_type: str = "minmax"

    # --- Artifact paths ---
    artifacts_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            ))),
            "artifacts",
        )
    )

    # --- Data quality ---
    max_fill_gap: int = 3          # max consecutive NaNs to forward-fill

    # --- LSTM architecture ---
    lstm_units_1: int = 128
    lstm_units_2: int = 64
    dense_units: int = 32
    dropout_rate: float = 0.2

    # --- Optimiser ---
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    reduce_lr_factor: float = 0.5

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @property
    def test_ratio(self) -> float:
        """Implied test fraction (1 - train - val)."""
        return round(1.0 - self.train_ratio - self.val_ratio, 6)

    @property
    def n_features(self) -> int:
        """Number of input features for the LSTM."""
        return len(self.feature_columns)

    @property
    def scaler_path(self) -> str:
        """Canonical path for the saved scaler."""
        return os.path.join(
            self.artifacts_dir,
            "scalers",
            f"scaler_{self.symbol}_{self.candle_interval}.pkl",
        )

    @property
    def model_path(self) -> str:
        """Canonical path for the saved Keras model."""
        return os.path.join(
            self.artifacts_dir,
            "models",
            f"lstm_{self.symbol}_{self.candle_interval}.keras",
        )

    @property
    def metadata_path(self) -> str:
        """Canonical path for pipeline metadata JSON."""
        return os.path.join(
            self.artifacts_dir,
            "results",
            f"metadata_{self.symbol}_{self.candle_interval}.json",
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Raise ValueError for obviously invalid configurations."""
        valid_intervals = {"1min", "5min", "15min", "1hour", "1day"}
        if self.candle_interval not in valid_intervals:
            raise ValueError(
                f"candle_interval must be one of {valid_intervals}, "
                f"got '{self.candle_interval}'"
            )
        if not (0.0 < self.train_ratio < 1.0):
            raise ValueError(f"train_ratio must be in (0, 1), got {self.train_ratio}")
        if not (0.0 < self.val_ratio < 1.0):
            raise ValueError(f"val_ratio must be in (0, 1), got {self.val_ratio}")
        if self.train_ratio + self.val_ratio >= 1.0:
            raise ValueError(
                "train_ratio + val_ratio must be < 1.0 to leave room for test set"
            )
        if self.sequence_length < 1:
            raise ValueError(f"sequence_length must be >= 1, got {self.sequence_length}")
        if self.target_horizon < 1:
            raise ValueError(f"target_horizon must be >= 1, got {self.target_horizon}")
        if not self.feature_columns:
            raise ValueError("feature_columns must not be empty")
        if self.target_column not in self.feature_columns:
            raise ValueError(
                f"target_column '{self.target_column}' must be in feature_columns"
            )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Convert to a plain dict (JSON-serialisable)."""
        d = asdict(self)
        # derived properties are not in asdict — add them explicitly
        d["test_ratio"] = self.test_ratio
        d["n_features"] = self.n_features
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineConfig":
        """
        Construct a PipelineConfig from a dict (e.g. loaded from JSON).
        Unknown keys are silently ignored to allow forward-compatibility.
        """
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
