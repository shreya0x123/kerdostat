"""
Shared pytest fixtures for the Kerdostat test suite.

Provides reusable fixtures for sample DataFrames, pre-computed
indicator dictionaries, and SignalEngine instances.
"""

import os
import sys

# Ensure the project root is on sys.path for absolute imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import pytest

from data.loaders import load_csv
from ml.indicators.technical_indicators import compute_all_indicators
from ml.signals.signal_engine import SignalEngine


# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the sample OHLCV CSV as a DataFrame."""
    return load_csv(SAMPLE_CSV)


@pytest.fixture
def sample_indicators(sample_df) -> dict:
    """Pre-computed indicator dictionary from sample data."""
    return compute_all_indicators(sample_df)


@pytest.fixture
def engine() -> SignalEngine:
    """Fresh SignalEngine instance."""
    return SignalEngine()


@pytest.fixture
def buy_indicators() -> dict:
    """
    Synthetic indicator values that should trigger a BUY signal.
    RSI < 30, MACD histogram > 0, Close < BB lower.
    """
    return {
        "rsi": 22.5,
        "ema_20": 180.00,
        "macd_line": 1.50,
        "macd_signal": 0.80,
        "macd_histogram": 0.70,
        "bb_upper": 190.00,
        "bb_middle": 182.00,
        "bb_lower": 174.00,
        "close": 172.00,
    }


@pytest.fixture
def sell_indicators() -> dict:
    """
    Synthetic indicator values that should trigger a SELL signal.
    RSI > 70, MACD histogram < 0, Close > BB upper.
    """
    return {
        "rsi": 78.5,
        "ema_20": 180.00,
        "macd_line": -1.20,
        "macd_signal": -0.50,
        "macd_histogram": -0.70,
        "bb_upper": 188.00,
        "bb_middle": 182.00,
        "bb_lower": 176.00,
        "close": 192.00,
    }


@pytest.fixture
def hold_indicators() -> dict:
    """
    Synthetic indicator values that should trigger a HOLD signal.
    RSI in neutral zone, mixed MACD/BB signals.
    """
    return {
        "rsi": 52.0,
        "ema_20": 180.00,
        "macd_line": 0.10,
        "macd_signal": 0.08,
        "macd_histogram": 0.02,
        "bb_upper": 188.00,
        "bb_middle": 182.00,
        "bb_lower": 176.00,
        "close": 181.00,
    }
