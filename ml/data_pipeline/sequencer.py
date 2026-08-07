"""
Kerdostat ML Data Pipeline — Sequencer
=======================================
Converts a normalised feature array into (X, y) sliding-window sequences
and performs a chronological train / validation / test split.

Sliding window logic:
    For a sequence_length of 30 and target_horizon of 1:
        X[i] = scaled_array[i : i + 30]         (shape: 30, n_features)
        y[i] = raw_close[i + 30 + 1 - 1]        (next Close price in $)

    y is stored in RAW (unscaled) Close price space so that evaluation
    metrics (MAE, RMSE, MAPE) are directly interpretable in dollars.
    This means the LSTM output is inverse-transformed before comparison.

Data leakage prevention:
    - Split is performed on the ORIGINAL index before windowing is applied
      to training vs. validation vs. test.
    - Scaler was fit only on training rows — this class receives already-
      scaled arrays and raw Close values, so no leakage can occur here.

Usage:
    from ml.data_pipeline.sequencer import Sequencer

    seq = Sequencer(config)
    bundle = seq.create_sequences(
        scaled_train, scaled_val, scaled_test,
        raw_close_train, raw_close_val, raw_close_test,
    )
    print(bundle.X_train.shape)   # (n_samples, seq_len, n_features)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class SequenceSplit:
    """Raw DataFrames split chronologically before windowing."""
    train: pd.DataFrame
    val:   pd.DataFrame
    test:  pd.DataFrame
    train_ratio: float
    val_ratio:   float
    test_ratio:  float


@dataclass
class DataBundle:
    """
    The final output of the full data preprocessing pipeline.

    X arrays shape: (n_samples, sequence_length, n_features)
    y arrays shape: (n_samples,)  — raw dollar Close prices
    """
    X_train: np.ndarray
    X_val:   np.ndarray
    X_test:  np.ndarray
    y_train: np.ndarray
    y_val:   np.ndarray
    y_test:  np.ndarray
    metadata: dict

    # Convenience
    @property
    def train_size(self) -> int:
        return len(self.X_train)

    @property
    def val_size(self) -> int:
        return len(self.X_val)

    @property
    def test_size(self) -> int:
        return len(self.X_test)

    @property
    def input_shape(self) -> tuple:
        """(sequence_length, n_features) — input shape for Keras."""
        return self.X_train.shape[1], self.X_train.shape[2]

    def summary(self) -> str:
        sl, nf = self.input_shape
        return (
            f"DataBundle | train={self.train_size} val={self.val_size} "
            f"test={self.test_size} | seq_len={sl} features={nf}"
        )


class Sequencer:
    """
    Performs chronological splitting and sliding-window sequence generation.

    Two-phase process:
        1. split_dataframe()  — split the feature DataFrame chronologically.
        2. create_sequences() — apply sliding window to each split and
                               collect targets from raw Close prices.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Phase 1: Chronological split
    # ------------------------------------------------------------------
    def split_dataframe(self, df: pd.DataFrame) -> SequenceSplit:
        """
        Split df chronologically into train / val / test.

        Ratios come from config: train_ratio, val_ratio, test_ratio.
        No shuffling — temporal order is preserved.

        Args:
            df: Full feature DataFrame (output of FeatureEngineer.compute).

        Returns:
            SequenceSplit with three DataFrames.
        """
        n = len(df)
        train_end = int(n * self.config.train_ratio)
        val_end   = train_end + int(n * self.config.val_ratio)

        train = df.iloc[:train_end]
        val   = df.iloc[train_end:val_end]
        test  = df.iloc[val_end:]

        logger.info(
            "Split: train=%d val=%d test=%d (total=%d)",
            len(train), len(val), len(test), n,
        )
        return SequenceSplit(
            train=train,
            val=val,
            test=test,
            train_ratio=self.config.train_ratio,
            val_ratio=self.config.val_ratio,
            test_ratio=self.config.test_ratio,
        )

    # ------------------------------------------------------------------
    # Phase 2: Sequence generation
    # ------------------------------------------------------------------
    def make_sequences(
        self,
        scaled_array: np.ndarray,
        raw_close: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Build (X, y) pairs from a scaled feature array.

        Args:
            scaled_array: Shape (n_rows, n_features) — scaled features.
            raw_close:    Shape (n_rows,) — raw dollar Close prices.

        Returns:
            (X, y) where:
                X shape: (n_sequences, sequence_length, n_features)
                y shape: (n_sequences,) — raw dollar Close price at t+horizon
        """
        seq_len  = self.config.sequence_length
        horizon  = self.config.target_horizon
        n        = len(scaled_array)

        if n < seq_len + horizon:
            raise ValueError(
                f"Array too short to build sequences: {n} rows, "
                f"need at least {seq_len + horizon} "
                f"(seq_len={seq_len} + horizon={horizon})."
            )

        X_list, y_list = [], []
        for i in range(n - seq_len - horizon + 1):
            X_list.append(scaled_array[i : i + seq_len])
            # Target: raw Close price at the prediction horizon step
            y_list.append(raw_close[i + seq_len + horizon - 1])

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        logger.debug("make_sequences: X=%s  y=%s", X.shape, y.shape)
        return X, y

    def make_sequences_scaled_y(
        self,
        scaled_array: np.ndarray,
        close_col_idx: int,
    ) -> tuple:
        """
        Build (X, y_scaled) pairs where y targets are in [0, 1] scaled space.

        This variant is used during LSTM *training* so that both inputs (X)
        and targets (y) are in the same normalised scale.  The evaluator then
        uses Normalizer.inverse_transform_close() to convert predictions back
        to raw dollar prices before computing MAE / RMSE / MAPE.

        At inference time or in the existing DataBundle tests, use
        make_sequences() (raw-dollar y) instead — it is NOT changed.

        Args:
            scaled_array:  Shape (n_rows, n_features) — normalised features.
            close_col_idx: Index of the Close column in scaled_array.
                           Obtained from Normalizer.close_idx.

        Returns:
            (X, y_scaled):
                X shape: (n_sequences, sequence_length, n_features)
                y shape: (n_sequences,) — scaled Close values in [0, 1]
        """
        seq_len = self.config.sequence_length
        horizon = self.config.target_horizon
        n       = len(scaled_array)

        if n < seq_len + horizon:
            raise ValueError(
                f"Array too short to build sequences: {n} rows, "
                f"need at least {seq_len + horizon} "
                f"(seq_len={seq_len} + horizon={horizon})."
            )

        scaled_close = scaled_array[:, close_col_idx]

        X_list, y_list = [], []
        for i in range(n - seq_len - horizon + 1):
            X_list.append(scaled_array[i : i + seq_len])
            # Scaled Close at the prediction horizon step
            y_list.append(scaled_close[i + seq_len + horizon - 1])

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        logger.debug("make_sequences_scaled_y: X=%s  y=%s", X.shape, y.shape)
        return X, y

    def create_bundle(
        self,
        split: SequenceSplit,
        scaled_train: np.ndarray,
        scaled_val:   np.ndarray,
        scaled_test:  np.ndarray,
    ) -> DataBundle:
        """
        Build a DataBundle from pre-scaled arrays and raw split DataFrames.

        Raw Close prices are extracted from the split DataFrames (before
        scaling) to serve as y targets and for evaluation in dollar space.

        Args:
            split:         SequenceSplit from split_dataframe().
            scaled_train:  Normalizer-scaled training array.
            scaled_val:    Normalizer-scaled validation array.
            scaled_test:   Normalizer-scaled test array.

        Returns:
            DataBundle with X/y for train/val/test.
        """
        close_col = self.config.target_column

        raw_close_train = split.train[close_col].values.astype(np.float32)
        raw_close_val   = split.val[close_col].values.astype(np.float32)
        raw_close_test  = split.test[close_col].values.astype(np.float32)

        X_train, y_train = self.make_sequences(scaled_train, raw_close_train)
        X_val,   y_val   = self.make_sequences(scaled_val,   raw_close_val)
        X_test,  y_test  = self.make_sequences(scaled_test,  raw_close_test)

        metadata = {
            "sequence_length": self.config.sequence_length,
            "target_horizon":  self.config.target_horizon,
            "n_features":      self.config.n_features,
            "feature_columns": self.config.feature_columns,
            "train_size":      len(X_train),
            "val_size":        len(X_val),
            "test_size":       len(X_test),
            "split_ratios": {
                "train": split.train_ratio,
                "val":   split.val_ratio,
                "test":  split.test_ratio,
            },
        }

        bundle = DataBundle(
            X_train=X_train, X_val=X_val, X_test=X_test,
            y_train=y_train, y_val=y_val, y_test=y_test,
            metadata=metadata,
        )
        logger.info(bundle.summary())
        return bundle
