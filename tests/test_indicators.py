"""
Tests for Technical Indicators
==============================
Validates the correctness, shape, and value ranges of all four
technical indicators: RSI, EMA, MACD, and Bollinger Bands.

Also validates the aggregated `compute_all_indicators` output
that serves as the contract for the SignalEngine and XDI engine.
"""

import numpy as np
import pandas as pd
import pytest

from ml.indicators.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    compute_all_indicators,
)


# ==================================================================
# RSI Tests
# ==================================================================
class TestRSI:
    """Tests for the Relative Strength Index calculation."""

    def test_rsi_range(self, sample_df):
        """RSI values must be between 0 and 100 (inclusive)."""
        rsi = calculate_rsi(sample_df)
        valid = rsi.dropna()
        assert (valid >= 0).all(), "RSI contains values below 0"
        assert (valid <= 100).all(), "RSI contains values above 100"

    def test_rsi_length(self, sample_df):
        """RSI series length must match input DataFrame length."""
        rsi = calculate_rsi(sample_df, period=14)
        assert len(rsi) == len(sample_df), (
            f"RSI length {len(rsi)} != DataFrame length {len(sample_df)}"
        )

    def test_rsi_has_valid_values(self, sample_df):
        """RSI should have non-NaN values after the lookback period."""
        rsi = calculate_rsi(sample_df, period=14)
        # After the first 14 rows, RSI should be computed
        valid_portion = rsi.iloc[14:]
        assert not valid_portion.isna().all(), "RSI is all NaN after lookback period"


# ==================================================================
# EMA Tests
# ==================================================================
class TestEMA:
    """Tests for the Exponential Moving Average calculation."""

    def test_ema_length(self, sample_df):
        """EMA series length must match input DataFrame length."""
        ema = calculate_ema(sample_df, span=20)
        assert len(ema) == len(sample_df), (
            f"EMA length {len(ema)} != DataFrame length {len(sample_df)}"
        )

    def test_ema_values_are_smoothed(self, sample_df):
        """EMA should be smoother than raw close prices (lower std dev)."""
        ema = calculate_ema(sample_df, span=20)
        valid_ema = ema.dropna()
        valid_close = sample_df["Close"].iloc[-len(valid_ema):]

        # EMA standard deviation should be less than or equal to raw close
        assert valid_ema.std() <= valid_close.std() + 1e-6, (
            "EMA is not smoother than raw close prices"
        )


# ==================================================================
# MACD Tests
# ==================================================================
class TestMACD:
    """Tests for the MACD calculation."""

    def test_macd_returns_three_series(self, sample_df):
        """MACD must return exactly three pd.Series (line, signal, histogram)."""
        result = calculate_macd(sample_df)
        assert len(result) == 3, f"MACD returned {len(result)} items, expected 3"
        for i, series in enumerate(result):
            assert isinstance(series, pd.Series), (
                f"MACD result[{i}] is {type(series)}, expected pd.Series"
            )

    def test_macd_histogram_is_difference(self, sample_df):
        """Histogram must equal MACD line minus Signal line."""
        macd_line, signal_line, histogram = calculate_macd(sample_df)

        # Drop NaN values for comparison
        valid_mask = ~(macd_line.isna() | signal_line.isna() | histogram.isna())
        expected = macd_line[valid_mask] - signal_line[valid_mask]
        actual = histogram[valid_mask]

        np.testing.assert_allclose(
            actual.values,
            expected.values,
            atol=1e-10,
            err_msg="MACD histogram != macd_line - signal_line",
        )


# ==================================================================
# Bollinger Bands Tests
# ==================================================================
class TestBollingerBands:
    """Tests for the Bollinger Bands calculation."""

    def test_bollinger_bands_ordering(self, sample_df):
        """Lower band ≤ Middle band ≤ Upper band must always hold."""
        upper, middle, lower = calculate_bollinger_bands(sample_df)

        # Drop NaN values
        valid_mask = ~(upper.isna() | middle.isna() | lower.isna())
        u = upper[valid_mask]
        m = middle[valid_mask]
        l = lower[valid_mask]

        assert (l <= m).all(), "Lower band exceeds middle band"
        assert (m <= u).all(), "Middle band exceeds upper band"


# ==================================================================
# compute_all_indicators Tests
# ==================================================================
class TestComputeAllIndicators:
    """Tests for the aggregated indicator output."""

    EXPECTED_KEYS = {
        "rsi",
        "ema_20",
        "macd_line",
        "macd_signal",
        "macd_histogram",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "close",
    }

    def test_output_has_all_keys(self, sample_indicators):
        """Output dict must contain all 9 expected keys."""
        assert set(sample_indicators.keys()) == self.EXPECTED_KEYS, (
            f"Missing keys: {self.EXPECTED_KEYS - set(sample_indicators.keys())}"
        )

    def test_output_has_no_nan(self, sample_indicators):
        """No NaN values should be present in the aggregated output."""
        for key, value in sample_indicators.items():
            assert not np.isnan(value), f"NaN found in indicator '{key}'"
            assert isinstance(value, float), (
                f"Indicator '{key}' is {type(value)}, expected float"
            )
