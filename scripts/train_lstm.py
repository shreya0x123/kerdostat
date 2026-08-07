#!/usr/bin/env python3
"""
Kerdostat — LSTM Training Entry Point
======================================
Command-line script to train the LSTM price-forecasting model.

This script ONLY orchestrates existing modules. All logic lives in:
    ml/training/training_session.py
    ml/data_pipeline/
    ml/models/

Usage:
    # Train on sample CSV (for testing):
    python scripts/train_lstm.py --source csv --filepath data/sample_ohlcv.csv

    # Train on real Alpaca data:
    python scripts/train_lstm.py \\
        --source alpaca \\
        --symbol AAPL \\
        --interval 1day \\
        --start 2020-01-01 \\
        --end 2025-01-01 \\
        --seq-len 60 \\
        --epochs 100

    # Quick smoke-test run:
    python scripts/train_lstm.py --source csv --filepath data/sample_ohlcv.csv \\
        --seq-len 3 --epochs 2

Environment variables for Alpaca API (alternative to passing explicitly):
    APCA_API_KEY_ID
    APCA_API_SECRET_KEY
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Add project root to path so all ml.* imports resolve correctly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.data_pipeline.config import PipelineConfig
from ml.training.training_session import TrainingSession


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kerdostat — LSTM model training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # --- Data source ---
    parser.add_argument(
        "--source", choices=["csv", "alpaca"], default="csv",
        help="Data source (default: csv)"
    )
    parser.add_argument(
        "--filepath", default=None,
        help="Path to CSV file (required when --source csv)"
    )
    parser.add_argument(
        "--symbol", default="AAPL",
        help="Ticker symbol (required when --source alpaca)"
    )
    parser.add_argument(
        "--interval", default="1day",
        choices=["1min", "5min", "15min", "1hour", "1day"],
        help="Candle interval (default: 1day)"
    )
    parser.add_argument(
        "--start", default="2020-01-01",
        help="Start date YYYY-MM-DD (default: 2020-01-01)"
    )
    parser.add_argument(
        "--end", default="2025-01-01",
        help="End date YYYY-MM-DD (default: 2025-01-01)"
    )

    # --- Model hyper-parameters ---
    parser.add_argument(
        "--seq-len", type=int, default=60,
        help="Sequence length (default: 60)"
    )
    parser.add_argument(
        "--horizon", type=int, default=1,
        help="Forecast horizon in candles (default: 1)"
    )
    parser.add_argument(
        "--epochs", type=int, default=100,
        help="Maximum training epochs (default: 100)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="Training batch size (default: 32)"
    )
    parser.add_argument(
        "--units-1", type=int, default=128,
        help="Units in first LSTM layer (default: 128)"
    )
    parser.add_argument(
        "--units-2", type=int, default=64,
        help="Units in second LSTM layer (default: 64)"
    )
    parser.add_argument(
        "--dropout", type=float, default=0.2,
        help="Dropout rate (default: 0.2)"
    )
    parser.add_argument(
        "--lr", type=float, default=0.001,
        help="Learning rate (default: 0.001)"
    )
    parser.add_argument(
        "--patience", type=int, default=10,
        help="EarlyStopping patience (default: 10)"
    )

    # --- Alpaca credentials ---
    parser.add_argument("--api-key", default=None, help="Alpaca API key")
    parser.add_argument("--api-secret", default=None, help="Alpaca API secret")

    # --- Misc ---
    parser.add_argument(
        "--artifacts-dir", default=None,
        help="Override artifacts directory (default: <project>/artifacts)"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)"
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "═" * 65)
    print("  Kerdostat — LSTM Training Pipeline")
    print("═" * 65)
    print(f"  Symbol        : {args.symbol}")
    print(f"  Interval      : {args.interval}")
    print(f"  Source        : {args.source}")
    if args.source == "csv":
        print(f"  CSV file      : {args.filepath}")
    else:
        print(f"  Date range    : {args.start} → {args.end}")
    print(f"  Seq length    : {args.seq_len}")
    print(f"  Horizon       : {args.horizon}")
    print(f"  LSTM units    : {args.units_1} / {args.units_2}")
    print(f"  Max epochs    : {args.epochs}  (patience={args.patience})")
    print("═" * 65)

    # Build config
    cfg_kwargs = dict(
        symbol=args.symbol,
        candle_interval=args.interval,
        start_date=args.start,
        end_date=args.end,
        sequence_length=args.seq_len,
        target_horizon=args.horizon,
        lstm_units_1=args.units_1,
        lstm_units_2=args.units_2,
        dropout_rate=args.dropout,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        epochs=args.epochs,
        early_stopping_patience=args.patience,
    )
    if args.artifacts_dir:
        cfg_kwargs["artifacts_dir"] = args.artifacts_dir

    cfg = PipelineConfig(**cfg_kwargs)

    # Run training
    session = TrainingSession(cfg)
    result = session.run(
        data_source=args.source,
        filepath=args.filepath,
        api_key=args.api_key,
        api_secret=args.api_secret,
    )

    result.print_summary()

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
