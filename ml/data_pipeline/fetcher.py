"""
Kerdostat ML Data Pipeline — Data Fetcher
==========================================
Thin wrapper around the existing Day 1 data loaders.

This module does NOT duplicate any loading logic. It delegates to:
    data.loaders.load_csv    — for local CSV files
    data.loaders.load_alpaca — for Alpaca API data

Additional responsibility vs. the raw loaders:
    - Validates that the returned DataFrame has enough rows for the
      configured sequence_length (at least seq_len + 35 indicator warm-up).
    - Returns the DataFrame together with fetch metadata for auditability.

Usage:
    from ml.data_pipeline.fetcher import DataFetcher
    from ml.data_pipeline.config import PipelineConfig

    cfg = PipelineConfig(symbol="AAPL")
    fetcher = DataFetcher(cfg)

    df, meta = fetcher.fetch_csv("data/sample_ohlcv.csv")
    df, meta = fetcher.fetch_alpaca()   # uses cfg.symbol / start / end
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Tuple

import pandas as pd

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches raw OHLCV data from either CSV or the Alpaca API.

    The class is intentionally thin — its only job beyond delegation
    is minimum-row validation so downstream modules can assume the
    DataFrame is large enough for indicator computation and sequencing.
    """

    # Minimum rows required = MACD warm-up (35) + 1 sequence + 1 target
    _INDICATOR_WARMUP: int = 35

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._min_rows = self._INDICATOR_WARMUP + config.sequence_length + 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_csv(self, filepath: str) -> Tuple[pd.DataFrame, dict]:
        """
        Load OHLCV data from a CSV file.

        Args:
            filepath: Path to the CSV file.

        Returns:
            (df, metadata) where metadata records the source and row count.

        Raises:
            FileNotFoundError: Propagated from load_csv.
            ValueError: If the DataFrame has too few rows.
        """
        logger.info("Fetching CSV data from: %s", filepath)

        # Delegate to the existing Day 1 loader — no logic duplication
        from data.loaders import load_csv
        df = load_csv(filepath)

        self._validate_row_count(df, source=f"csv:{filepath}")

        meta = self._build_metadata(df, source="csv", filepath=filepath)
        logger.info("CSV fetch complete — %d rows loaded", len(df))
        return df, meta

    def fetch_alpaca(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Fetch OHLCV bar data from the Alpaca API.

        Credentials can be supplied directly or via environment variables
        (APCA_API_KEY_ID / APCA_API_SECRET_KEY).

        Returns:
            (df, metadata).

        Raises:
            ValueError: If credentials are missing or row count is too low.
            RuntimeError: If the Alpaca API request fails.
        """
        symbol = self.config.symbol
        start  = self.config.start_date
        end    = self.config.end_date

        logger.info(
            "Fetching Alpaca data — symbol=%s  %s → %s",
            symbol, start, end,
        )

        from data.loaders import load_alpaca
        df = load_alpaca(
            symbol=symbol,
            start=start,
            end=end,
            api_key=api_key,
            api_secret=api_secret,
        )

        self._validate_row_count(df, source=f"alpaca:{symbol}")

        meta = self._build_metadata(
            df, source="alpaca", symbol=symbol, start=start, end=end
        )
        logger.info("Alpaca fetch complete — %d rows loaded for %s", len(df), symbol)
        return df, meta

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _validate_row_count(self, df: pd.DataFrame, source: str) -> None:
        """Raise ValueError if the DataFrame is too short."""
        if len(df) < self._min_rows:
            raise ValueError(
                f"Insufficient data from '{source}': {len(df)} rows. "
                f"Need at least {self._min_rows} rows "
                f"({self._INDICATOR_WARMUP} indicator warm-up + "
                f"{self.config.sequence_length} sequence length + 1 target)."
            )

    @staticmethod
    def _build_metadata(
        df: pd.DataFrame,
        source: str,
        **kwargs,
    ) -> dict:
        """Construct a metadata dict for auditability."""
        meta = {
            "source": source,
            "rows": len(df),
            "columns": list(df.columns),
            "date_start": str(df.index[0]),
            "date_end": str(df.index[-1]),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        meta.update(kwargs)
        return meta
