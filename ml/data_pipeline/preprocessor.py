"""
Kerdostat ML Data Pipeline — Preprocessor (Orchestrator)
==========================================================
Single entry point that chains the full Day 4 pipeline:

    DataFetcher → DataCleaner → FeatureEngineer →
    Sequencer.split → Normalizer (fit on train) →
    Sequencer.create_bundle → DataBundle

Nothing new is implemented here — this module wires together the other
Day 4 components and handles artifact persistence (saving the scaler,
metadata, and optionally the numpy arrays to disk).

Usage:
    from ml.data_pipeline.preprocessor import DataPreprocessor
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig(symbol="AAPL", sequence_length=30)
    preprocessor = DataPreprocessor(cfg)

    # From CSV (development / offline)
    bundle, norm = preprocessor.run_from_csv("data/sample_ohlcv.csv")

    # From Alpaca (production)
    bundle, norm = preprocessor.run_from_alpaca()

    # Access data
    print(bundle.X_train.shape)    # (n, 30, 14)
    print(bundle.y_train[:5])      # [187.23, 188.10, ...]
"""

from __future__ import annotations

import json
import logging
import os
from typing import Tuple

import numpy as np

from ml.data_pipeline.cleaner import DataCleaner
from ml.data_pipeline.config import PipelineConfig
from ml.data_pipeline.feature_engineer import FeatureEngineer
from ml.data_pipeline.fetcher import DataFetcher
from ml.data_pipeline.normalizer import Normalizer
from ml.data_pipeline.sequencer import DataBundle, Sequencer

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Orchestrates the complete Day 4 data pipeline.

    Each public run_* method returns a (DataBundle, Normalizer) tuple.
    The Normalizer is returned so that:
        1. The caller can save it with normalizer.save().
        2. The LSTM predictor can reload it at inference time for
           inverse-transforming predicted Close prices to dollar space.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        config.validate()    # Fail fast on invalid config

        self._fetcher  = DataFetcher(config)
        self._cleaner  = DataCleaner(config)
        self._engineer = FeatureEngineer(config)
        self._sequencer = Sequencer(config)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def run_from_csv(
        self,
        filepath: str,
        save_artifacts: bool = True,
    ) -> Tuple[DataBundle, Normalizer]:
        """
        Run the full pipeline from a local CSV file.

        Args:
            filepath:       Path to the OHLCV CSV.
            save_artifacts: If True, saves the scaler + metadata to disk.

        Returns:
            (DataBundle, fitted Normalizer)
        """
        logger.info("=== DataPreprocessor: CSV pipeline start ===")

        df_raw, fetch_meta = self._fetcher.fetch_csv(filepath)
        return self._run_pipeline(df_raw, fetch_meta, save_artifacts)

    def run_from_alpaca(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        save_artifacts: bool = True,
    ) -> Tuple[DataBundle, Normalizer]:
        """
        Run the full pipeline fetching data from the Alpaca API.

        Args:
            api_key:        Alpaca API key (or env var).
            api_secret:     Alpaca API secret (or env var).
            save_artifacts: If True, saves the scaler + metadata to disk.

        Returns:
            (DataBundle, fitted Normalizer)
        """
        logger.info("=== DataPreprocessor: Alpaca pipeline start ===")

        df_raw, fetch_meta = self._fetcher.fetch_alpaca(api_key, api_secret)
        return self._run_pipeline(df_raw, fetch_meta, save_artifacts)

    # ------------------------------------------------------------------
    # Core pipeline (shared by both entry points)
    # ------------------------------------------------------------------
    def _run_pipeline(
        self,
        df_raw,
        fetch_meta: dict,
        save_artifacts: bool,
    ) -> Tuple[DataBundle, Normalizer]:
        """Execute clean → engineer → split → normalise → sequence."""

        # Step 1: Clean
        df_clean, clean_report = self._cleaner.clean(df_raw)
        logger.info("Cleaning: %s", clean_report)

        # Step 2: Feature engineering (reuses Day 1 indicator functions)
        df_features = self._engineer.compute(df_clean)
        logger.info(
            "Features: %d rows × %d columns", len(df_features), df_features.shape[1]
        )

        # Step 3: Chronological split (before scaling — no leakage)
        split = self._sequencer.split_dataframe(df_features)

        # Step 4: Normalise (scaler fit on train only)
        normalizer = Normalizer(self.config)
        scaled_train = normalizer.fit_transform(split.train)
        scaled_val   = normalizer.transform(split.val)
        scaled_test  = normalizer.transform(split.test)

        # Step 5: Create sliding-window sequences
        bundle = self._sequencer.create_bundle(
            split, scaled_train, scaled_val, scaled_test
        )

        # Enrich bundle metadata with pipeline context
        bundle.metadata.update({
            "fetch": fetch_meta,
            "cleaning": str(clean_report),
            "config": self.config.to_dict(),
        })

        # Step 6: Persist artifacts
        if save_artifacts:
            self._save_artifacts(normalizer, bundle)

        logger.info("=== DataPreprocessor: pipeline complete ===")
        logger.info(bundle.summary())
        return bundle, normalizer

    # ------------------------------------------------------------------
    # Artifact persistence
    # ------------------------------------------------------------------
    def _save_artifacts(self, normalizer: Normalizer, bundle: DataBundle) -> None:
        """Save scaler, metadata, and optional numpy arrays."""
        # Scaler
        scaler_path = normalizer.save()
        logger.info("Scaler saved → %s", scaler_path)

        # Metadata JSON
        meta_path = self.config.metadata_path
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump(bundle.metadata, f, indent=2, default=str)
        logger.info("Metadata saved → %s", meta_path)

        # Numpy arrays (optional — useful for fast reloading during training)
        data_dir = os.path.join(self.config.artifacts_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        prefix = os.path.join(
            data_dir, f"{self.config.symbol}_{self.config.candle_interval}"
        )
        np.save(f"{prefix}_X_train.npy", bundle.X_train)
        np.save(f"{prefix}_X_val.npy",   bundle.X_val)
        np.save(f"{prefix}_X_test.npy",  bundle.X_test)
        np.save(f"{prefix}_y_train.npy", bundle.y_train)
        np.save(f"{prefix}_y_val.npy",   bundle.y_val)
        np.save(f"{prefix}_y_test.npy",  bundle.y_test)
        logger.info("Numpy arrays saved → %s_*.npy", prefix)
