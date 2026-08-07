"""
Kerdostat Data Loaders
======================
Unified OHLCV data loading from CSV files and the Alpaca Markets API.

Both loaders return a pandas DataFrame with columns:
    Open, High, Low, Close, Volume
indexed by Date (ascending order).

Usage:
    from data.loaders import load_csv, load_alpaca

    df = load_csv("data/sample_ohlcv.csv")
    df = load_alpaca("AAPL", "2025-01-01", "2025-03-01")
"""

import os
from datetime import datetime

import pandas as pd


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file.

    The CSV must contain columns: Date, Open, High, Low, Close, Volume.
    The Date column is parsed and set as the index.

    Args:
        filepath: Path to the CSV file (absolute or relative to project root).

    Returns:
        pd.DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume],
        sorted by date ascending.

    Raises:
        FileNotFoundError: If the filepath does not exist.
        ValueError: If required columns are missing.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"OHLCV file not found: {filepath}")

    df = pd.read_csv(filepath, parse_dates=["Date"], index_col="Date")

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Expected: {required_columns}"
        )

    # Ensure numeric types
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by date ascending
    df = df.sort_index(ascending=True)

    return df


def load_alpaca(
    symbol: str,
    start: str,
    end: str,
    api_key: str | None = None,
    api_secret: str | None = None,
    paper: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV bar data from the Alpaca Markets API.

    Requires the `alpaca-py` package. Credentials can be passed directly
    or read from environment variables APCA_API_KEY_ID and APCA_API_SECRET_KEY.

    Args:
        symbol: Ticker symbol (e.g. "AAPL").
        start: Start date string in "YYYY-MM-DD" format.
        end: End date string in "YYYY-MM-DD" format.
        api_key: Alpaca API key (or set APCA_API_KEY_ID env var).
        api_secret: Alpaca API secret (or set APCA_API_SECRET_KEY env var).
        paper: If True, use the paper trading endpoint.

    Returns:
        pd.DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume],
        sorted by date ascending.

    Raises:
        ImportError: If alpaca-py is not installed.
        ValueError: If API credentials are not provided.
        RuntimeError: If the API request fails.
    """
    # Resolve credentials
    api_key = api_key or os.environ.get("APCA_API_KEY_ID")
    api_secret = api_secret or os.environ.get("APCA_API_SECRET_KEY")

    if not api_key or not api_secret:
        raise ValueError(
            "Alpaca API credentials required. "
            "Pass api_key/api_secret or set APCA_API_KEY_ID and "
            "APCA_API_SECRET_KEY environment variables."
        )

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError:
        raise ImportError(
            "alpaca-py is required for Alpaca data loading. "
            "Install it with: pip install alpaca-py"
        )

    try:
        client = StockHistoricalDataClient(api_key, api_secret)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.strptime(start, "%Y-%m-%d"),
            end=datetime.strptime(end, "%Y-%m-%d"),
        )

        bars = client.get_stock_bars(request_params)
        df = bars.df

        # If multi-index (symbol, timestamp), drop the symbol level
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel("symbol")

        # Rename columns to match our standard schema
        column_mapping = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df = df.rename(columns=column_mapping)

        # Keep only the columns we need
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        # Ensure index name is Date
        df.index.name = "Date"

        # Sort by date ascending
        df = df.sort_index(ascending=True)

        return df

    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch data from Alpaca for {symbol}: {e}"
        ) from e
