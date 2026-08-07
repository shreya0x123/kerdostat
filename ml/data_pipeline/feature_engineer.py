"""
Kerdostat ML Data Pipeline — Feature Engineer
=============================================
Builds a feature-rich DataFrame by computing technical indicators
across the FULL time series (not just the last row as in compute_all_indicators).

Key design principle:
    This module REUSES the existing Day 1 indicator functions directly:
        calculate_rsi, calculate_ema, calculate_macd,
        calculate_bollinger_bands

    It does NOT duplicate any indicator logic. The difference is that it
    attaches the full Series as new columns rather than extracting only
    the last value.

Output feature columns (14 total):
    OHLCV (5):  Open, High, Low, Close, Volume
    RSI (1):    RSI
    EMA (1):    EMA_20
    MACD (3):   MACD_Line, MACD_Signal, MACD_Histogram
    BB (4):     BB_Upper, BB_Middle, BB_Lower, BB_Width

Usage:
    from ml.data_pipeline.feature_engineer import FeatureEngineer
    from ml.data_pipeline.config import PipelineConfig

    engineer = FeatureEngineer(PipelineConfig())
    df_features = engineer.compute(df_clean)
"""

from __future__ import annotations

import logging

import pandas as pd

from ml.data_pipeline.config import PipelineConfig
from ml.indicators.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Appends technical indicator columns to the cleaned OHLCV DataFrame.

    Reuses the Day 1 indicator functions without modification.
    After computation, the initial NaN rows (from indicator warm-up)
    are dropped so the returned DataFrame is fully dense.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all feature columns and return a clean feature DataFrame.

        Args:
            df: Cleaned OHLCV DataFrame (output of DataCleaner.clean).

        Returns:
            DataFrame with the same DatetimeIndex and the following columns:
            Open, High, Low, Close, Volume, RSI, EMA_20,
            MACD_Line, MACD_Signal, MACD_Histogram,
            BB_Upper, BB_Middle, BB_Lower, BB_Width

        Raises:
            ValueError: If required columns are missing.
        """
        df = df.copy()
        rows_in = len(df)
        logger.info("Computing features on %d rows", rows_in)

        # ----------------------------------------------------------
        # Day 1 indicator functions — called on the full time series
        # ----------------------------------------------------------
        # RSI (14)
        df["RSI"] = calculate_rsi(df)

        # EMA (20)
        df["EMA_20"] = calculate_ema(df)

        # MACD (12, 26, 9)
        macd_line, macd_signal, macd_hist = calculate_macd(df)
        df["MACD_Line"]      = macd_line
        df["MACD_Signal"]    = macd_signal
        df["MACD_Histogram"] = macd_hist

        # Bollinger Bands (20, σ=2)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df)
        df["BB_Upper"]  = bb_upper
        df["BB_Middle"] = bb_middle
        df["BB_Lower"]  = bb_lower

        # Derived: Bollinger Band Width (volatility proxy)
        df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]

        # ----------------------------------------------------------
        # Drop warm-up NaNs introduced by indicator computation
        # ----------------------------------------------------------
        df = df.dropna()

        rows_out = len(df)
        rows_dropped = rows_in - rows_out
        logger.info(
            "Feature engineering complete — %d → %d rows "
            "(%d warm-up rows dropped)",
            rows_in, rows_out, rows_dropped,
        )

        # Keep only the configured feature columns
        available_features = [
            c for c in self.config.feature_columns if c in df.columns
        ]
        missing_features = [
            c for c in self.config.feature_columns if c not in df.columns
        ]
        if missing_features:
            raise ValueError(
                f"Feature columns not found in DataFrame: {missing_features}. "
                f"Available: {list(df.columns)}"
            )

        return df[available_features]

    @property
    def feature_names(self) -> list[str]:
        """Convenience accessor for the ordered feature column list."""
        return list(self.config.feature_columns)
