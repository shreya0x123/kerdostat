"""
Kerdostat ML Data Pipeline — Data Cleaner
==========================================
Validates and cleans raw OHLCV DataFrames before feature engineering.

Cleaning steps (applied in order):
    1. Assert required columns exist (Open, High, Low, Close, Volume).
    2. Coerce all OHLCV columns to float64.
    3. Remove duplicate timestamps (keep last occurrence).
    4. Sort chronologically ascending.
    5. Forward-fill short NaN gaps (≤ max_fill_gap consecutive).
    6. Drop rows that still have any NaN after gap-filling.
    7. Validate OHLC sanity: High ≥ Low, Close within [Low, High].
    8. Report a CleaningReport with before/after row counts.

Usage:
    from ml.data_pipeline.cleaner import DataCleaner
    from ml.data_pipeline.config import PipelineConfig

    cleaner = DataCleaner(PipelineConfig())
    df_clean, report = cleaner.clean(df_raw)
    print(report)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

import pandas as pd

from ml.data_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}


@dataclass
class CleaningReport:
    """Summary of what the cleaner did to the DataFrame."""
    rows_before: int
    rows_after: int
    duplicates_removed: int
    nan_rows_filled: int
    nan_rows_dropped: int
    ohlc_violations_fixed: int

    def __str__(self) -> str:
        return (
            f"CleaningReport | "
            f"rows: {self.rows_before} → {self.rows_after} | "
            f"duplicates removed: {self.duplicates_removed} | "
            f"NaN rows filled: {self.nan_rows_filled} | "
            f"NaN rows dropped: {self.nan_rows_dropped} | "
            f"OHLC violations fixed: {self.ohlc_violations_fixed}"
        )


class DataCleaner:
    """
    Validates and cleans a raw OHLCV DataFrame.

    Designed to be run after DataFetcher and before FeatureEngineer.
    All operations are non-destructive on the input (a copy is returned).
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, CleaningReport]:
        """
        Apply the full cleaning pipeline.

        Args:
            df: Raw OHLCV DataFrame with DatetimeIndex.

        Returns:
            (cleaned_df, CleaningReport)

        Raises:
            ValueError: If required columns are missing after cleaning.
        """
        df = df.copy()
        rows_before = len(df)

        # Step 1: Validate columns
        self._assert_required_columns(df)

        # Step 2: Coerce dtypes
        df = self._coerce_dtypes(df)

        # Step 3: Remove duplicates
        n_before_dedup = len(df)
        df = df[~df.index.duplicated(keep="last")]
        duplicates_removed = n_before_dedup - len(df)
        if duplicates_removed:
            logger.warning("Removed %d duplicate timestamps", duplicates_removed)

        # Step 4: Sort chronologically
        df = df.sort_index(ascending=True)

        # Step 5: Forward-fill short NaN gaps
        nan_before = df.isnull().any(axis=1).sum()
        df = df.ffill(limit=self.config.max_fill_gap)
        nan_after_fill = df.isnull().any(axis=1).sum()
        nan_rows_filled = nan_before - nan_after_fill

        # Step 6: Drop remaining NaN rows
        df = df.dropna()
        nan_rows_dropped = nan_after_fill
        if nan_rows_dropped:
            logger.warning("Dropped %d rows with unfillable NaNs", nan_rows_dropped)

        # Step 7: OHLC sanity check + fix
        violations = self._fix_ohlc_violations(df)

        report = CleaningReport(
            rows_before=rows_before,
            rows_after=len(df),
            duplicates_removed=duplicates_removed,
            nan_rows_filled=nan_rows_filled,
            nan_rows_dropped=nan_rows_dropped,
            ohlc_violations_fixed=violations,
        )
        logger.info("Cleaning complete: %s", report)
        return df, report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _assert_required_columns(df: pd.DataFrame) -> None:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"DataFrame is missing required OHLCV columns: {sorted(missing)}"
            )

    @staticmethod
    def _coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all OHLCV columns are float64."""
        for col in REQUIRED_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _fix_ohlc_violations(df: pd.DataFrame) -> int:
        """
        Clamp High/Low so that High >= Low >= 0 and Close ∈ [Low, High].
        Returns the count of rows where a violation was found and fixed.
        """
        violations = 0

        # Identify violated rows
        bad_high_low = df["High"] < df["Low"]
        if bad_high_low.any():
            # Swap High and Low where violated
            df.loc[bad_high_low, ["High", "Low"]] = (
                df.loc[bad_high_low, ["Low", "High"]].values
            )
            violations += bad_high_low.sum()
            logger.warning(
                "Fixed %d rows where High < Low", bad_high_low.sum()
            )

        # Clamp Close within [Low, High]
        close_below_low = df["Close"] < df["Low"]
        close_above_high = df["Close"] > df["High"]
        out_of_range = close_below_low | close_above_high
        if out_of_range.any():
            df.loc[close_below_low, "Close"] = df.loc[close_below_low, "Low"]
            df.loc[close_above_high, "Close"] = df.loc[close_above_high, "High"]
            violations += out_of_range.sum()
            logger.warning(
                "Clamped Close to [Low, High] for %d rows", out_of_range.sum()
            )

        return violations
