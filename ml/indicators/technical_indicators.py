"""
Kerdostat Technical Indicators
==============================
Pure pandas/numpy implementations of four core technical indicators
used by the signal engine. No external TA libraries required.

Indicators:
    - RSI (Relative Strength Index)
    - EMA (Exponential Moving Average)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands

All functions accept a DataFrame with a 'Close' column and return
pandas Series or tuples of Series.

The `compute_all_indicators` function aggregates the latest values
from all four indicators into a single dictionary — the standard
input format for the SignalEngine and the Day 3 XDI engine.
"""

import numpy as np
import pandas as pd


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI).

    RSI measures the speed and magnitude of recent price changes
    to evaluate overbought or oversold conditions.

    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS  = avg_gain / avg_loss  (using Wilder's smoothing)

    Args:
        df: DataFrame with a 'Close' column.
        period: Lookback period (default 14).

    Returns:
        pd.Series of RSI values (0–100). First `period` values are NaN.
    """
    close = df["Close"]
    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothed moving average (equivalent to EMA with alpha=1/period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def calculate_ema(df: pd.DataFrame, span: int = 20) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA).

    EMA gives more weight to recent prices, making it more responsive
    to new information than a simple moving average.

    Args:
        df: DataFrame with a 'Close' column.
        span: The EMA window / span (default 20).

    Returns:
        pd.Series of EMA values. First `span-1` values are NaN.
    """
    return df["Close"].ewm(span=span, min_periods=span, adjust=False).mean()


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate the Moving Average Convergence Divergence (MACD).

    MACD is a trend-following momentum indicator showing the relationship
    between two EMAs of the closing price.

    Components:
        MACD Line  = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal)
        Histogram   = MACD Line - Signal Line

    Args:
        df: DataFrame with a 'Close' column.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        Tuple of (macd_line, signal_line, histogram) as pd.Series.
    """
    close = df["Close"]

    ema_fast = close.ewm(span=fast, min_periods=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, min_periods=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, min_periods=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: int = 2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Bollinger Bands consist of a middle band (SMA) with an upper and lower
    band placed at standard deviations above and below the middle band.

    Components:
        Middle Band = SMA(period)
        Upper Band  = Middle + std_dev * rolling_std
        Lower Band  = Middle - std_dev * rolling_std

    Args:
        df: DataFrame with a 'Close' column.
        period: SMA lookback period (default 20).
        std_dev: Number of standard deviations (default 2).

    Returns:
        Tuple of (upper_band, middle_band, lower_band) as pd.Series.
    """
    close = df["Close"]

    middle = close.rolling(window=period, min_periods=period).mean()
    rolling_std = close.rolling(window=period, min_periods=period).std()

    upper = middle + (std_dev * rolling_std)
    lower = middle - (std_dev * rolling_std)

    return upper, middle, lower


def compute_all_indicators(df: pd.DataFrame) -> dict:
    """
    Compute all four indicators and aggregate the latest values
    into a single dictionary.

    This is the standard input format for the SignalEngine and
    the contract consumed by Day 3's XDI (Explainable Decision
    Inference) engine.

    Args:
        df: DataFrame with OHLCV columns (must have 'Close').

    Returns:
        Dictionary with keys:
            rsi, ema_20, macd_line, macd_signal, macd_histogram,
            bb_upper, bb_middle, bb_lower, close

    Raises:
        ValueError: If the DataFrame has insufficient rows for
                    indicator computation (needs >= 35 rows for
                    MACD slow=26 + signal=9).
    """
    min_rows = 35  # slow(26) + signal(9) for MACD
    if len(df) < min_rows:
        raise ValueError(
            f"DataFrame has {len(df)} rows but needs at least {min_rows} "
            f"for reliable indicator computation."
        )

    rsi = calculate_rsi(df)
    ema = calculate_ema(df)
    macd_line, macd_signal, macd_histogram = calculate_macd(df)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df)

    # Get the latest (most recent) values
    indicators = {
        "rsi": round(float(rsi.iloc[-1]), 4),
        "ema_20": round(float(ema.iloc[-1]), 4),
        "macd_line": round(float(macd_line.iloc[-1]), 4),
        "macd_signal": round(float(macd_signal.iloc[-1]), 4),
        "macd_histogram": round(float(macd_histogram.iloc[-1]), 4),
        "bb_upper": round(float(bb_upper.iloc[-1]), 4),
        "bb_middle": round(float(bb_middle.iloc[-1]), 4),
        "bb_lower": round(float(bb_lower.iloc[-1]), 4),
        "close": round(float(df["Close"].iloc[-1]), 4),
    }

    return indicators
