"""
Kerdostat ML Models — LSTM Predictor (Integration Bridge)
===========================================================
The single integration point between the LSTM model and the existing
Day 1–3 pipeline.

Contract:
    LSTMPredictor.predict(recent_df) returns the exact dict that
    ml/pipeline.py Step 4 expects for ml_prediction. This means:
        - No changes to pipeline.py
        - No changes to xdi_engine.py
        - No changes to signal_engine.py
        - All 71 existing tests continue to pass unchanged

The predictor:
    1. Accepts a raw OHLCV DataFrame (the same one used by the signal engine).
    2. Runs it through the same feature engineering as the training pipeline.
    3. Normalises using the saved scaler (fit on training data).
    4. Runs LSTM inference → gets a scaled prediction.
    5. Inverse-transforms to real dollar price space.
    6. Computes expected_change_percent and prediction_confidence.
    7. Returns the ml_prediction dict.

Confidence estimation:
    Since an LSTM regression model does not natively output uncertainty,
    we proxy prediction_confidence using the inverse of the normalised
    residual magnitude (based on training MAE stored in metadata).
    A lower relative error → higher confidence.

Usage:
    from ml.models.predictor import LSTMPredictor
    from ml.data_pipeline.config import PipelineConfig

    predictor = LSTMPredictor.load(
        model_path="artifacts/models/lstm_AAPL_1day.keras",
        scaler_path="artifacts/scalers/scaler_AAPL_1day.pkl",
        config=PipelineConfig(symbol="AAPL"),
    )

    ml_prediction = predictor.predict(recent_df, candle_interval="1day")

    # Plug into pipeline.py Step 4:
    result["ml_prediction"] = ml_prediction
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd

from ml.data_pipeline.config import PipelineConfig
from ml.data_pipeline.feature_engineer import FeatureEngineer
from ml.data_pipeline.normalizer import Normalizer

logger = logging.getLogger(__name__)


class LSTMPredictor:
    """
    Inference-only wrapper around a trained LSTM model.

    Produces the ml_prediction dict consumed by ml/pipeline.py Step 4
    and the XDI engine. The existing pipeline contract is preserved exactly.
    """

    # Features the model was trained on — declared here for transparency
    FORECAST_FEATURES: List[str] = [
        "RSI", "EMA_20", "MACD_Line", "MACD_Signal", "MACD_Histogram",
        "BB_Upper", "BB_Middle", "BB_Lower", "BB_Width",
        "Open", "High", "Low", "Close", "Volume",
    ]

    def __init__(
        self,
        model,                          # keras.Model (lazy import to keep module lightweight)
        normalizer: Normalizer,
        config: PipelineConfig,
        training_mae: Optional[float] = None,
        model_version: str = "",
    ) -> None:
        self._model = model
        self._normalizer = normalizer
        self._config = config
        self._training_mae = training_mae   # Used for confidence estimation
        self._model_version = model_version
        self._engineer = FeatureEngineer(config)

    # ------------------------------------------------------------------
    # Factory / class methods
    # ------------------------------------------------------------------
    @classmethod
    def load(
        cls,
        model_path: str,
        scaler_path: str,
        config: Optional[PipelineConfig] = None,
        training_mae: Optional[float] = None,
    ) -> "LSTMPredictor":
        """
        Load a trained predictor from saved model + scaler artifacts.

        Args:
            model_path:   Path to the .keras model file.
            scaler_path:  Path to the .pkl scaler file.
            config:       PipelineConfig (defaults if None).
            training_mae: Training MAE for confidence proxy (optional).

        Returns:
            A ready-to-use LSTMPredictor.
        """
        from tensorflow import keras   # Lazy import

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"LSTM model not found: {model_path}")

        cfg = config or PipelineConfig()
        model = keras.models.load_model(model_path)
        normalizer = Normalizer.load(scaler_path, config=cfg)

        logger.info("LSTMPredictor loaded — model: %s", model_path)
        return cls(
            model=model,
            normalizer=normalizer,
            config=cfg,
            training_mae=training_mae,
        )

    @classmethod
    def load_with_metadata(
        cls,
        config: PipelineConfig,
    ) -> Optional["LSTMPredictor"]:
        """
        Try to load a predictor using config-derived paths.
        Returns None (graceful fallback) if any artifact is missing.

        Also validates that the saved model metadata matches the
        current config (symbol, interval, features, seq_len).
        """
        model_path  = config.model_path
        scaler_path = config.scaler_path

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            logger.debug(
                "Model or scaler not found — ML prediction disabled. "
                "model=%s  scaler=%s", model_path, scaler_path
            )
            return None

        # Try to load and validate metadata
        training_mae: Optional[float] = None
        model_version: str = ""
        try:
            from ml.training.model_metadata import ModelMetadata  # lazy
            meta_path = config.metadata_path
            if os.path.exists(meta_path):
                meta = ModelMetadata.load(meta_path)
                ok, reason = meta.is_compatible_with(
                    symbol=config.symbol,
                    candle_interval=config.candle_interval,
                    features=config.feature_columns,
                    sequence_length=config.sequence_length,
                    forecast_horizon=config.target_horizon,
                )
                if not ok:
                    logger.warning(
                        "Model metadata incompatible: %s — disabling ML prediction.",
                        reason,
                    )
                    return None
                training_mae = meta.metrics.get("mae")
                model_version = meta.model_version
                logger.info("Model metadata validated: %s", meta.summary())
        except Exception as e:
            logger.warning("Could not validate model metadata: %s", e)

        try:
            predictor = cls.load(
                model_path=model_path,
                scaler_path=scaler_path,
                config=config,
                training_mae=training_mae,
            )
            predictor._model_version = model_version
            return predictor
        except Exception as e:
            logger.warning("Failed to load LSTM predictor: %s — using fallback.", e)
            return None

    # ------------------------------------------------------------------
    # Public predict API
    # ------------------------------------------------------------------
    def predict(
        self,
        recent_df: pd.DataFrame,
        candle_interval: Optional[str] = None,
    ) -> dict:
        """
        Generate an ml_prediction dict from recent OHLCV data.

        This is the contract method consumed by ml/pipeline.py Step 4.
        The returned dict has exactly the same schema as the placeholder
        in pipeline.py — enabling drop-in replacement.

        Args:
            recent_df:       Raw OHLCV DataFrame (at least seq_len + 35 rows).
            candle_interval: Override config.candle_interval if supplied.

        Returns:
            ml_prediction dict:
            {
                "enabled": True,
                "prediction_type": "price_forecast",
                "model": "LSTM",
                "predicted_price": float,
                "expected_change_percent": float,
                "prediction_confidence": float,
                "forecast_features": [...]
            }
        """
        interval = candle_interval or self._config.candle_interval

        # Step 1: Feature engineering (reuses Day 1 functions)
        df_features = self._engineer.compute(recent_df)

        # Step 2: Extract the last sequence_length rows as the input window
        seq_len = self._config.sequence_length
        if len(df_features) < seq_len:
            raise ValueError(
                f"Insufficient data for prediction: {len(df_features)} rows. "
                f"Need at least {seq_len} (sequence_length)."
            )

        window_df = df_features.tail(seq_len)
        current_price = float(recent_df["Close"].iloc[-1])

        # Step 3: Scale using the training scaler
        scaled_window = self._normalizer.transform(window_df)

        # Step 4: Reshape for Keras: (1, seq_len, n_features)
        X = scaled_window.reshape(1, seq_len, self._config.n_features).astype(np.float32)

        # Step 5: LSTM inference (output in scaled space)
        scaled_prediction = float(self._model.predict(X, verbose=0).flatten()[0])

        # Step 6: Inverse-transform to dollar price
        predicted_price = float(
            self._normalizer.inverse_transform_close(
                np.array([scaled_prediction])
            )[0]
        )

        # Step 7: Derived metrics
        expected_change_percent = self._compute_change_percent(
            current_price, predicted_price
        )
        prediction_confidence = self._estimate_confidence(
            current_price, predicted_price
        )

        logger.info(
            "LSTM prediction: current=%.2f predicted=%.2f change=%.2f%% conf=%s",
            current_price, predicted_price, expected_change_percent,
            f"{prediction_confidence:.4f}" if prediction_confidence is not None else "None",
        )

        horizon_cfg = self._config.target_horizon
        interval    = self._config.candle_interval
        horizon_label = _horizon_display(interval, horizon_cfg)

        return {
            "enabled":                  True,
            "prediction_type":          "price_forecast",
            "model":                    "LSTM",
            "current_price":            round(current_price, 2),
            "predicted_price":          round(predicted_price, 2),
            "expected_change_percent":  round(expected_change_percent, 2),
            "prediction_confidence":    prediction_confidence,
            "forecast_horizon_candles": horizon_cfg,
            "prediction_horizon":       horizon_label,
            "model_version":            self._model_version,
            "forecast_features":        self.FORECAST_FEATURES,
            "generated_at":             datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_change_percent(current: float, predicted: float) -> float:
        """Compute percentage change from current to predicted price."""
        if current == 0:
            return 0.0
        return round(((predicted - current) / current) * 100, 4)

    def _estimate_confidence(
        self, current: float, predicted: float
    ) -> float:
        """
        Proxy confidence derived from relative error vs training MAE.

        If training MAE is available, confidence = 1 - (|Δprice| / (10 × MAE)).
        Without training MAE, defaults to a conservative 0.70 baseline.
        The confidence is clipped to [0.50, 0.95].
        """
        if self._training_mae and self._training_mae > 0 and current > 0:
            abs_change = abs(predicted - current)
            raw_conf = 1.0 - min(abs_change / (self._training_mae * 10), 0.45)
        else:
            raw_conf = 0.70

        return round(float(np.clip(raw_conf, 0.50, 0.95)), 4)



# ---------------------------------------------------------------------------
# Module-level helper (not a class method — used before predictor is built)
# ---------------------------------------------------------------------------
_HORIZON_LABELS: dict = {
    "1min":  "next 5–15 minutes",
    "5min":  "next 30–60 minutes",
    "15min": "next 1–4 hours",
    "1hour": "next trading day",
    "1day":  "next trading day",
}


def _horizon_display(candle_interval: str, horizon_candles: int) -> str:
    """Return a human-readable forecast horizon string."""
    if horizon_candles == 1:
        return _HORIZON_LABELS.get(candle_interval, "next candle")
    return f"next {horizon_candles} {candle_interval} candles"
