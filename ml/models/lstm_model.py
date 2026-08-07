"""
Kerdostat ML Models — LSTM Architecture
=========================================
Builds the Keras LSTM model for financial time-series price forecasting.

Architecture:
    Input(seq_len, n_features)
        └── LSTM(units_1, return_sequences=True)
            └── Dropout(dropout_rate)
                └── LSTM(units_2, return_sequences=False)
                    └── Dropout(dropout_rate)
                        └── Dense(dense_units, activation='relu')
                            └── Dense(1)    ← predicted scaled Close price

Design rationale:
    - Two stacked LSTM layers capture both short-term patterns (layer 1,
      returns full sequence) and long-term context (layer 2, final state).
    - Dropout after each LSTM layer regularises against overfitting on
      financial time series (high noise, low signal-to-noise ratio).
    - Output layer is a single Dense(1) with linear activation because
      the target is a continuous price, not a classification.
    - All hyperparameters come from PipelineConfig — nothing is hardcoded.

Usage:
    from ml.models.lstm_model import LSTMModel
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig()
    model = LSTMModel(cfg)
    keras_model = model.build()
    keras_model.summary()
"""

from __future__ import annotations

import logging

import tensorflow as tf
from tensorflow import keras

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class LSTMModel:
    """
    Factory class for the Kerdostat LSTM architecture.

    Separates model construction from training and inference so that
    each concern is independently testable.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._model: keras.Model | None = None

    def build(self) -> keras.Model:
        """
        Construct and compile the LSTM model.

        Returns:
            A compiled keras.Model ready for training.
        """
        seq_len   = self.config.sequence_length
        n_features = self.config.n_features
        cfg = self.config

        inputs = keras.Input(shape=(seq_len, n_features), name="ohlcv_sequence")

        # --- First LSTM layer (returns full sequence for stacking) ---
        x = keras.layers.LSTM(
            units=cfg.lstm_units_1,
            return_sequences=True,
            name="lstm_1",
            kernel_regularizer=keras.regularizers.l2(1e-4),
        )(inputs)
        x = keras.layers.Dropout(cfg.dropout_rate, name="dropout_1")(x)

        # --- Second LSTM layer (returns only the final state) ---
        x = keras.layers.LSTM(
            units=cfg.lstm_units_2,
            return_sequences=False,
            name="lstm_2",
            kernel_regularizer=keras.regularizers.l2(1e-4),
        )(x)
        x = keras.layers.Dropout(cfg.dropout_rate, name="dropout_2")(x)

        # --- Dense head ---
        x = keras.layers.Dense(
            cfg.dense_units,
            activation="relu",
            name="dense_hidden",
        )(x)
        outputs = keras.layers.Dense(1, name="price_output")(x)

        model = keras.Model(inputs=inputs, outputs=outputs, name="kerdostat_lstm")

        # Compile with Adam and MSE loss (standard for regression)
        optimizer = keras.optimizers.Adam(learning_rate=cfg.learning_rate)
        model.compile(
            optimizer=optimizer,
            loss="mean_squared_error",
            metrics=["mae"],
        )

        self._model = model

        logger.info(
            "LSTM model built — input: (%d, %d), params: %d",
            seq_len, n_features, model.count_params(),
        )
        return model

    @property
    def model(self) -> keras.Model:
        """Return the built model, raising if build() has not been called."""
        if self._model is None:
            raise RuntimeError("Model has not been built yet. Call build() first.")
        return self._model

    def architecture_summary(self) -> str:
        """Return a human-readable architecture description."""
        cfg = self.config
        return (
            f"KerdoStat LSTM Architecture\n"
            f"  Input:    ({cfg.sequence_length}, {cfg.n_features})\n"
            f"  LSTM-1:   {cfg.lstm_units_1} units, return_sequences=True\n"
            f"  Dropout:  {cfg.dropout_rate}\n"
            f"  LSTM-2:   {cfg.lstm_units_2} units, return_sequences=False\n"
            f"  Dropout:  {cfg.dropout_rate}\n"
            f"  Dense:    {cfg.dense_units} units (ReLU)\n"
            f"  Output:   1 unit (linear) — predicted Close price\n"
            f"  Optimizer: Adam (lr={cfg.learning_rate})\n"
            f"  Loss:      MSE\n"
        )
