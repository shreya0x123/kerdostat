"""
Kerdostat ML Training — Training Session
=========================================
Full end-to-end training pipeline orchestrator for Day 6.

Responsibilities:
    1. Accept a PipelineConfig (or auto-build one from symbol/interval).
    2. Fetch and preprocess historical data via the existing Day 4 pipeline.
    3. Build LSTM model using Day 5 LSTMModel.
    4. Train with SCALED y targets (fixes the scale-mismatch bug from Day 5).
    5. Evaluate on the held-out test set in RAW DOLLAR SPACE.
    6. Compute naive baseline and compare.
    7. Compute directional accuracy.
    8. Save: model, scaler, plots, history JSON, metadata JSON.
    9. Produce a data summary before training starts.
    10. Return a TrainingResult dataclass.

Scale-mismatch fix (critical for real training):
    Day 4/5 DataBundle stores y_train/y_test as raw dollar prices (e.g. $185).
    LSTM inputs X are in [0,1] scale. Training MSE between a [0,1] output and
    a $185 target would make the loss useless. Fix: use make_sequences_scaled_y()
    so both X and y are in [0,1] during training. For evaluation/reporting,
    inverse-transform predictions → dollars before computing MAE/RMSE/MAPE.

Usage (from CLI or notebook):
    from ml.training.training_session import TrainingSession
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig(
        symbol="AAPL", candle_interval="1day",
        sequence_length=60, start_date="2020-01-01", end_date="2025-01-01",
    )
    session = TrainingSession(cfg)
    result = session.run(data_source="csv", filepath="data/sample_ohlcv.csv")
    print(result.metadata.summary())
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ml.data_pipeline.config import PipelineConfig
from ml.data_pipeline.preprocessor import DataPreprocessor
from ml.data_pipeline.sequencer import Sequencer
from ml.training.baseline import NaiveBaseline
from ml.training.metrics import compute_metrics, directional_accuracy
from ml.training.model_metadata import ModelMetadata

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Structured result returned by TrainingSession.run()."""
    success: bool
    metadata: ModelMetadata
    epochs_trained: int = 0
    best_val_loss: float = float("inf")
    model_path: str = ""
    scaler_path: str = ""
    plot_path: str = ""
    history_path: str = ""
    beats_baseline: Optional[bool] = None
    error_message: str = ""

    def print_summary(self) -> None:
        """Print a human-readable training summary to stdout."""
        sep = "=" * 65
        print(f"\n{sep}")
        print(f"  TRAINING COMPLETE — {self.metadata.symbol} / "
              f"{self.metadata.candle_interval}")
        print(sep)
        if not self.success:
            print(f"  ERROR: {self.error_message}")
            return

        m = self.metadata.metrics
        b = self.metadata.baseline_metrics
        da_raw = m.get("directional_accuracy")
        da_str = f"{da_raw*100:.1f}%" if da_raw is not None else "N/A"

        print(f"  Training epochs : {self.epochs_trained}")
        print(f"  Best val loss   : {self.best_val_loss:.6f}")
        print()
        print(f"  {'Metric':<12} {'Baseline':>12} {'LSTM':>12} {'vs Baseline':>14}")
        print(f"  {'-'*54}")
        for key in ("mae", "rmse", "mape"):
            bv = b.get(key) or 0
            mv = m.get(key) or 0
            diff = (bv - mv) / bv * 100 if bv != 0 else 0
            sign = "+" if diff > 0 else ""
            unit = "$" if key != "mape" else "%"
            print(f"  {key.upper():<12} {bv:>11.4f}{unit} {mv:>11.4f}{unit} "
                  f"{sign}{diff:>10.1f}%")
        print(f"  {'Dir. Acc.':<12} {'N/A':>12} {da_str:>12}")
        print()
        verdict = "✅ BEATS" if self.beats_baseline else "❌ DOES NOT BEAT"
        print(f"  VERDICT: LSTM {verdict} the naive baseline on RMSE")
        print(f"\n  Model saved  : {self.model_path}")
        print(f"  Scaler saved : {self.scaler_path}")
        if self.plot_path:
            print(f"  Plot saved   : {self.plot_path}")
        print(f"{sep}\n")


class TrainingSession:
    """
    Orchestrates a complete LSTM training run.

    Does NOT contain any ML business logic — it wires together the
    existing Day 4 (data pipeline) and Day 5 (model) modules.
    """

    MIN_TRAINING_SAMPLES = 50   # Guard against tiny datasets

    def __init__(self, config: PipelineConfig) -> None:
        config.validate()
        self.config = config
        self._preprocessor = DataPreprocessor(config)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(
        self,
        data_source: str = "csv",
        filepath: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> TrainingResult:
        """
        Execute the full training pipeline.

        Args:
            data_source: "csv" or "alpaca".
            filepath:    CSV path (required when data_source="csv").
            api_key:     Alpaca key (required when data_source="alpaca").
            api_secret:  Alpaca secret (required when data_source="alpaca").

        Returns:
            TrainingResult with all metrics and artifact paths.
        """
        try:
            return self._run_pipeline(data_source, filepath, api_key, api_secret)
        except Exception as exc:
            logger.exception("Training session failed: %s", exc)
            return TrainingResult(
                success=False,
                metadata=ModelMetadata(
                    symbol=self.config.symbol,
                    candle_interval=self.config.candle_interval,
                ),
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------
    def _run_pipeline(
        self,
        data_source: str,
        filepath: Optional[str],
        api_key: Optional[str],
        api_secret: Optional[str],
    ) -> TrainingResult:

        cfg = self.config

        # ---- Step 1: Fetch and preprocess data ----
        logger.info("Step 1: Loading and preprocessing data (%s)", data_source)

        if data_source == "csv":
            if not filepath:
                raise ValueError("filepath required when data_source='csv'")
            bundle, normalizer = self._preprocessor.run_from_csv(
                filepath, save_artifacts=True
            )
        elif data_source == "alpaca":
            bundle, normalizer = self._preprocessor.run_from_alpaca(
                api_key=api_key, api_secret=api_secret, save_artifacts=True
            )
        else:
            raise ValueError(f"Unknown data_source '{data_source}'. Use 'csv' or 'alpaca'.")

        self._print_data_summary(bundle)

        # ---- Step 2: Build scaled-y sequences for training ----
        logger.info("Step 2: Building scaled-y training sequences")
        X_train_s, y_train_s = self._build_scaled_sequences(
            bundle.X_train, normalizer, bundle.metadata
        )
        X_val_s, y_val_s = self._build_scaled_sequences(
            bundle.X_val, normalizer, bundle.metadata
        )

        if len(X_train_s) < self.MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Insufficient training samples: {len(X_train_s)} "
                f"(minimum {self.MIN_TRAINING_SAMPLES}). "
                "Fetch more historical data or reduce sequence_length."
            )

        logger.info(
            "Training sequences: X_train=%s  y_train=%s  X_val=%s  y_val=%s",
            X_train_s.shape, y_train_s.shape, X_val_s.shape, y_val_s.shape,
        )

        # ---- Step 3: Build LSTM model ----
        logger.info("Step 3: Building LSTM architecture")
        from ml.models.lstm_model import LSTMModel  # lazy
        lstm = LSTMModel(cfg)
        model = lstm.build()
        logger.info("LSTM model built — total parameters: %d", model.count_params())

        # ---- Step 4: Train ----
        logger.info("Step 4: Training LSTM (max %d epochs, patience=%d)",
                    cfg.epochs, cfg.early_stopping_patience)
        from ml.models.trainer import ModelTrainer  # lazy
        trainer = ModelTrainer(cfg)
        history = trainer.train(model, X_train_s, y_train_s, X_val_s, y_val_s)

        epochs_trained = len(history.get("loss", []))
        best_val_loss = min(history.get("val_loss", [float("inf")]))
        logger.info("Training complete: %d epochs, best_val_loss=%.6f",
                    epochs_trained, best_val_loss)

        # ---- Step 5: Save model and history ----
        logger.info("Step 5: Saving model and training history")
        model_path = trainer.save_model(model)
        history_path = trainer.save_history(history)
        scaler_path = normalizer.save()

        # ---- Step 6: Evaluate on test set (raw dollar space) ----
        logger.info("Step 6: Evaluating on test set")
        from ml.models.evaluator import ModelEvaluator  # lazy
        evaluator = ModelEvaluator(cfg, normalizer)

        # NOTE: bundle.X_test / bundle.y_test use raw-dollar y (from DataBundle).
        # ModelEvaluator expects raw y_test for dollar-space comparison.
        eval_metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)

        test_metrics = compute_metrics(
            np.array(eval_metrics.actuals),
            np.array(eval_metrics.predictions),
        )
        da = directional_accuracy(
            np.array(eval_metrics.actuals),
            np.array(eval_metrics.predictions),
        )

        # ---- Step 7: Naive baseline ----
        logger.info("Step 7: Computing naive baseline")
        baseline = NaiveBaseline()
        baseline_metrics = baseline.compute_metrics(bundle.y_test)

        beats = baseline.beats(baseline_metrics, test_metrics)
        improvement = baseline.improvement_pct(baseline_metrics, test_metrics)
        logger.info(
            "LSTM %s baseline — RMSE improvement: %.1f%%",
            "BEATS" if beats else "does not beat", improvement,
        )

        # ---- Step 8: Save evaluation plot ----
        logger.info("Step 8: Saving evaluation plot")
        plot_path = ""
        try:
            plot_path = evaluator.plot(eval_metrics.actuals, eval_metrics.predictions)
        except Exception as e:
            logger.warning("Plot generation failed: %s", e)

        # ---- Step 9: Save metadata ----
        logger.info("Step 9: Saving model metadata")
        metadata = self._build_metadata(
            bundle=bundle,
            epochs_trained=epochs_trained,
            best_val_loss=best_val_loss,
            test_metrics=test_metrics,
            baseline_metrics=baseline_metrics,
            da=da,
            model_path=model_path,
            scaler_path=scaler_path,
        )
        metadata.stamp_version()
        metadata.compute_verdict()
        metadata_path = metadata.save()
        logger.info("Metadata: %s", metadata.summary())

        return TrainingResult(
            success=True,
            metadata=metadata,
            epochs_trained=epochs_trained,
            best_val_loss=best_val_loss,
            model_path=model_path,
            scaler_path=scaler_path,
            plot_path=plot_path,
            history_path=history_path,
            beats_baseline=beats,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_scaled_sequences(
        self,
        X: np.ndarray,
        normalizer,
        bundle_metadata: dict,
    ) -> tuple:
        """
        Extract scaled-y sequences from an already-windowed X array.

        X shape: (n_samples, seq_len, n_features)
        The last row of each X window is at index [seq_len - 1].
        The y target (scaled Close at horizon step) was NOT stored in the
        bundle — we recover it from X itself:

            y_scaled[i] = X[i, -horizon, close_idx]

        This works because make_sequences() uses contiguous windows and
        the horizon is 1 in the default config, so the target Close is
        the last time-step of window i+1, which equals X[i+1, -1, close_idx].

        For horizon=1:
            y_scaled[i] = X[i+1, -1, close_idx]   (next window's last Close)

        For horizon > 1 we fall back to recomputing from the scaled arrays.
        """
        close_idx = normalizer.close_idx
        horizon   = self.config.target_horizon
        seq_len   = self.config.sequence_length

        if close_idx is None:
            raise RuntimeError(
                "Normalizer.close_idx is None — scaler must be fitted first."
            )

        n = len(X)
        if n == 0:
            return X, np.array([], dtype=np.float32)

        # For horizon=1: y[i] = close value at seq_len+i in the full scaled array.
        # We can recover it directly from the next window's last timestep.
        # For horizon=1 and n windows: we have n-1 complete (X, y) pairs
        # where y[i] = X[i+1, -1, close_idx].
        # To keep shapes consistent with y_val having fewer samples, we use
        # X[i, seq_len-1+horizon-1] instead — but we only have seq_len steps.
        # Simplest robust method: use the last timestep of X[i] as the current
        # close; the target is the NEXT candle's close. Since X[i+1,0,...] =
        # X[i,1,...] (sliding window), X[i+1,-1,close_idx] is the target.
        # For the last window we don't have X[n]. Drop that sample.

        if horizon == 1 and n > 1:
            X_out = X[:-1]                                         # (n-1, seq_len, n_features)
            y_out = X[1:, -1, close_idx].astype(np.float32)       # (n-1,) — scaled Close
            return X_out, y_out

        # General case (horizon > 1): rebuild from the stacked X array.
        # Reconstruct the full scaled array by taking column sequences.
        # X[0, :, :] = scaled_array[0:seq_len, :]
        # X[1, :, :] = scaled_array[1:seq_len+1, :]  ...
        # => scaled_array[i, :] = X[i, 0, :]  for i in 0..n-1
        # The full array up to n + seq_len - 1 rows can be approximated.
        # For simplicity, use last step of each window:
        full_scaled = np.vstack([X[:, 0, :], X[-1, 1:, :]])  # approx reconstruction
        scaled_close = full_scaled[:, close_idx]

        y_list = []
        X_list = []
        for i in range(n - horizon):
            X_list.append(X[i])
            y_list.append(scaled_close[i + horizon])
        X_out = np.array(X_list, dtype=np.float32)
        y_out = np.array(y_list, dtype=np.float32)
        return X_out, y_out

    def _build_metadata(
        self,
        bundle,
        epochs_trained: int,
        best_val_loss: float,
        test_metrics: dict,
        baseline_metrics: dict,
        da,
        model_path: str,
        scaler_path: str,
    ) -> ModelMetadata:
        """Populate and return a ModelMetadata object from training results."""
        cfg = self.config
        bm = bundle.metadata

        meta = ModelMetadata(
            symbol=cfg.symbol,
            candle_interval=cfg.candle_interval,
            sequence_length=cfg.sequence_length,
            forecast_horizon=cfg.target_horizon,
            features=cfg.feature_columns,
            n_features=cfg.n_features,
            lstm_units_1=cfg.lstm_units_1,
            lstm_units_2=cfg.lstm_units_2,
            dense_units=cfg.dense_units,
            dropout_rate=cfg.dropout_rate,
            training_samples=int(bm.get("train_size", 0)),
            validation_samples=int(bm.get("val_size", 0)),
            test_samples=int(bm.get("test_size", 0)),
            train_ratio=cfg.train_ratio,
            val_ratio=cfg.val_ratio,
            epochs_trained=epochs_trained,
            best_val_loss=round(float(best_val_loss), 6),
            scaler_type=cfg.scaler_type,
            scaler_path=scaler_path,
            model_path=model_path,
        )

        meta.set_metrics(
            mae=test_metrics["mae"],
            rmse=test_metrics["rmse"],
            mape=test_metrics["mape"],
            directional_accuracy=da,
        )
        meta.set_baseline_metrics(
            mae=baseline_metrics["mae"],
            rmse=baseline_metrics["rmse"],
            mape=baseline_metrics["mape"],
        )
        return meta

    @staticmethod
    def _print_data_summary(bundle) -> None:
        """Print a data preparation summary table to stdout."""
        m = bundle.metadata
        sep = "─" * 55
        print(f"\n{sep}")
        print(f"  DATA PREPARATION SUMMARY")
        print(sep)
        print(f"  {'Sequence length':<30} : {m.get('sequence_length', '?')}")
        print(f"  {'Forecast horizon':<30} : {m.get('target_horizon', '?')}")
        print(f"  {'Number of features':<30} : {m.get('n_features', '?')}")
        print(f"  {'Training sequences':<30} : {m.get('train_size', '?')}")
        print(f"  {'Validation sequences':<30} : {m.get('val_size', '?')}")
        print(f"  {'Test sequences':<30} : {m.get('test_size', '?')}")
        print(sep + "\n")
