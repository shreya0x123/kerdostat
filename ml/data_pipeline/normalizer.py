"""
Kerdostat ML Data Pipeline — Normalizer
========================================
Fits a MinMaxScaler on training data and applies it to all splits.

Critical design: the scaler is fit ONLY on training data to prevent
data leakage. Validation and test sets are transformed using the
training-set scaler.

The scaler is persisted to disk (artifacts/scalers/) so it can be
reloaded at inference time for consistent inverse-transformation of
LSTM predictions back to real price space.

Usage:
    from ml.data_pipeline.normalizer import Normalizer
    from ml.data_pipeline.config import PipelineConfig

    norm = Normalizer(PipelineConfig())
    scaled_train = norm.fit_transform(train_df)
    scaled_val   = norm.transform(val_df)
    scaled_test  = norm.transform(test_df)
    norm.save()

    # Later at inference:
    norm2 = Normalizer.load(cfg.scaler_path)
    price = norm2.inverse_transform_close(predicted_value)
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class Normalizer:
    """
    Feature-wise MinMax normalisation (scales each column to [0, 1]).

    Maintains a separate reference to the Close-column scaler index
    so that LSTM output (a single scaled value) can be inverse-transformed
    back to a real dollar price.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._scaler: MinMaxScaler = MinMaxScaler(feature_range=(0, 1))
        self._is_fitted: bool = False

        # Index of the Close column in the feature matrix
        # Used for single-column inverse transform of LSTM predictions
        self._close_idx: Optional[int] = None

    # ------------------------------------------------------------------
    # Fit / Transform
    # ------------------------------------------------------------------
    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fit the scaler on df and return the scaled array.

        Must be called on TRAINING data only. Raises RuntimeError if
        called twice (to catch accidental re-fitting on val/test).

        Args:
            df: Training feature DataFrame.

        Returns:
            np.ndarray of shape (n_rows, n_features) scaled to [0, 1].
        """
        if self._is_fitted:
            raise RuntimeError(
                "Scaler is already fitted. Use transform() for val/test data."
            )

        self._record_close_index(df)
        scaled = self._scaler.fit_transform(df.values.astype(np.float32))
        self._is_fitted = True
        logger.info(
            "Scaler fitted on %d training rows, %d features",
            len(df), df.shape[1],
        )
        return scaled

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Apply the already-fitted scaler to df.

        Args:
            df: Validation or test feature DataFrame.

        Returns:
            np.ndarray scaled to [0, 1].

        Raises:
            RuntimeError: If called before fit_transform.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "Scaler has not been fitted yet. Call fit_transform() first."
            )
        return self._scaler.transform(df.values.astype(np.float32))

    def inverse_transform_close(self, scaled_values: np.ndarray) -> np.ndarray:
        """
        Inverse-transform a 1-D array of scaled Close predictions to
        the original price space.

        Args:
            scaled_values: 1-D or 2-D array of scaled predictions.

        Returns:
            np.ndarray of real dollar prices.

        Raises:
            RuntimeError: If the scaler has not been fitted.
        """
        if not self._is_fitted:
            raise RuntimeError("Scaler has not been fitted yet.")
        if self._close_idx is None:
            raise RuntimeError("Close column index not recorded during fit.")

        scaled_values = np.asarray(scaled_values).flatten()
        n_features = len(self.config.feature_columns)
        dummy = np.zeros((len(scaled_values), n_features), dtype=np.float32)
        dummy[:, self._close_idx] = scaled_values

        inversed = self._scaler.inverse_transform(dummy)
        return inversed[:, self._close_idx]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: Optional[str] = None) -> str:
        """
        Serialise the scaler to disk using pickle.

        Args:
            path: Override the default path from config.scaler_path.

        Returns:
            Absolute path where the scaler was saved.
        """
        save_path = path or self.config.scaler_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        payload = {
            "scaler": self._scaler,
            "close_idx": self._close_idx,
            "feature_columns": self.config.feature_columns,
            "is_fitted": self._is_fitted,
        }
        with open(save_path, "wb") as f:
            pickle.dump(payload, f)

        logger.info("Scaler saved to: %s", save_path)
        return save_path

    @classmethod
    def load(cls, path: str, config: Optional[PipelineConfig] = None) -> "Normalizer":
        """
        Load a previously saved scaler from disk.

        Args:
            path: Path to the .pkl file.
            config: Optional config (reconstructed from payload if None).

        Returns:
            A fitted Normalizer ready for transform() and inverse_transform_close().
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Scaler file not found: {path}")

        with open(path, "rb") as f:
            payload = pickle.load(f)

        instance = cls(config or PipelineConfig())
        instance._scaler = payload["scaler"]
        instance._close_idx = payload["close_idx"]
        instance._is_fitted = payload["is_fitted"]
        logger.info("Scaler loaded from: %s", path)
        return instance

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _record_close_index(self, df: pd.DataFrame) -> None:
        """Store the column index of 'Close' for later inverse transform."""
        cols = list(df.columns)
        if self.config.target_column not in cols:
            raise ValueError(
                f"Target column '{self.config.target_column}' not found in DataFrame. "
                f"Available: {cols}"
            )
        self._close_idx = cols.index(self.config.target_column)

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def close_idx(self) -> Optional[int]:
        return self._close_idx
