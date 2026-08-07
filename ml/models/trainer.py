"""
Kerdostat ML Models — Trainer
==============================
Handles model training, callback configuration, and model persistence.

Training strategy:
    - EarlyStopping on validation loss (patience from config, restores
      best weights automatically).
    - ReduceLROnPlateau: halves the learning rate if val_loss stalls.
    - ModelCheckpoint: saves the best model to artifacts/models/.
    - Training history is saved as JSON for post-hoc analysis.

Usage:
    from ml.models.trainer import ModelTrainer
    from ml.models.lstm_model import LSTMModel
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig(epochs=50, batch_size=32)
    lstm = LSTMModel(cfg)
    model = lstm.build()

    trainer = ModelTrainer(cfg)
    history = trainer.train(model, bundle.X_train, bundle.y_train,
                                   bundle.X_val,   bundle.y_val)
    trainer.save_model(model)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import numpy as np
import tensorflow as tf
from tensorflow import keras

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Configures training callbacks and runs the Keras training loop.

    Separates training logic from model architecture (LSTMModel) and
    evaluation logic (ModelEvaluator) so each can be tested independently.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def train(
        self,
        model: keras.Model,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Train the model with EarlyStopping and ReduceLROnPlateau.

        Args:
            model:   Compiled Keras model (from LSTMModel.build()).
            X_train: Shape (n, seq_len, n_features).
            y_train: Shape (n,) — raw Close prices.
            X_val:   Shape (m, seq_len, n_features).
            y_val:   Shape (m,) — raw Close prices.

        Returns:
            History dict {epoch: [...], loss: [...], val_loss: [...], ...}
        """
        cfg = self.config
        callbacks = self._build_callbacks()

        logger.info(
            "Training started — epochs=%d batch=%d train=%d val=%d",
            cfg.epochs, cfg.batch_size, len(X_train), len(X_val),
        )

        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=cfg.epochs,
            batch_size=cfg.batch_size,
            callbacks=callbacks,
            verbose=1,
            shuffle=False,          # Preserve temporal order within batch
        )

        epochs_run = len(history.history["loss"])
        best_val_loss = min(history.history["val_loss"])
        logger.info(
            "Training complete — %d epochs run, best val_loss=%.6f",
            epochs_run, best_val_loss,
        )

        return history.history

    def save_model(self, model: keras.Model, path: str | None = None) -> str:
        """
        Save the Keras model to disk in the native .keras format.

        Args:
            model: Trained Keras model.
            path:  Override default path from config.model_path.

        Returns:
            Absolute path where the model was saved.
        """
        save_path = path or self.config.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        model.save(save_path)
        logger.info("Model saved → %s", save_path)
        return save_path

    def save_history(self, history: Dict[str, Any], path: str | None = None) -> str:
        """
        Save training history dict to JSON for post-hoc analysis.

        Args:
            history: Return value of model.fit().history.history.
            path:    Override default path.

        Returns:
            Absolute path where the history JSON was saved.
        """
        results_dir = os.path.join(self.config.artifacts_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        default_name = (
            f"history_{self.config.symbol}_{self.config.candle_interval}.json"
        )
        save_path = path or os.path.join(results_dir, default_name)

        # Convert numpy float32 to plain floats for JSON serialisation
        serialisable = {
            k: [float(v) for v in vals]
            for k, vals in history.items()
        }
        with open(save_path, "w") as f:
            json.dump(serialisable, f, indent=2)

        logger.info("Training history saved → %s", save_path)
        return save_path

    @staticmethod
    def load_model(path: str) -> keras.Model:
        """
        Load a saved Keras model from disk.

        Args:
            path: Path to the .keras model file.

        Returns:
            Compiled Keras model.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        model = keras.models.load_model(path)
        logger.info("Model loaded from: %s", path)
        return model

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_callbacks(self) -> list:
        """Construct the Keras callbacks list from config."""
        cfg = self.config
        model_dir = os.path.dirname(cfg.model_path)
        os.makedirs(model_dir, exist_ok=True)

        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=cfg.early_stopping_patience,
                restore_best_weights=True,
                verbose=1,
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=cfg.reduce_lr_factor,
                patience=cfg.reduce_lr_patience,
                min_lr=1e-6,
                verbose=1,
            ),
            keras.callbacks.ModelCheckpoint(
                filepath=cfg.model_path,
                monitor="val_loss",
                save_best_only=True,
                verbose=0,
            ),
        ]
        return callbacks
