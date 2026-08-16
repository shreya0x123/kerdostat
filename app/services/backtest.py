"""
app/services/backtest.py
=========================
Day 13 — Signal Engine Backtest

Runs the existing signal engine over 30 days of historical data
and computes BUY/SELL precision and recall.

Methodology
-----------
For each trading day in the 30-day window:
  1. Fetch data UP TO that day (no lookahead bias).
  2. Run scan_for_signal() on the window.
  3. Record the signal (BUY/SELL/None) emitted.
  4. Determine ground truth: if price rose >1% next day → BUY correct;
     if price fell >1% next day → SELL correct.
  5. Accumulate TP/FP/TN/FN for BUY and SELL.
  6. Compute precision = TP / (TP + FP), recall = TP / (TP + FN).

Results are saved to artifacts/backtest_report.json.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "artifacts",
)
BACKTEST_JSON = os.path.join(ARTIFACTS_DIR, "backtest_report.json")

FORWARD_RETURN_THRESHOLD = 0.01  # ≥1% next-day change to label BUY/SELL correct


# ── Metric helpers ────────────────────────────────────────────────────────────

def _precision(tp: int, fp: int) -> float:
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0


def _recall(tp: int, fn: int) -> float:
    return tp / (tp + fn) if (tp + fn) > 0 else 0.0


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── Core backtest logic ───────────────────────────────────────────────────────

def run_backtest(
    symbol: str = "AAPL",
    lookback_days: int = 120,   # how many days of history to feed each window
    eval_window: int = 30,      # how many days to evaluate signals over
    use_mock_data: bool = False,
) -> dict:
    """
    Run a 30-day signal-engine backtest.

    Args:
        symbol        : Ticker to test.
        lookback_days : Historical bar count for indicator warm-up.
        eval_window   : Number of trading days to evaluate signals over.
        use_mock_data : If True, use generated mock OHLCV (for CI/offline mode).

    Returns:
        dict with full backtest metrics and metadata.
    """
    from app.services.signal_engine import (
        fetch_ohlcv, compute_indicators, scan_for_signal, generate_mock_ohlcv,
        RSI_OVERSOLD, RSI_OVERBOUGHT, EMA_SHORT, EMA_LONG,
        MACD_FAST, MACD_SLOW, MACD_SIGNAL_PERIOD,
    )

    logger.info("Backtest starting — symbol=%s eval_window=%d", symbol, eval_window)

    # ── Fetch full historical data ────────────────────────────────────────────
    if use_mock_data:
        df_full = generate_mock_ohlcv(symbol, period="6mo")
    else:
        try:
            df_full = fetch_ohlcv(symbol, period="6mo")
        except Exception as exc:
            logger.warning("Live data fetch failed (%s) — using mock data.", exc)
            df_full = generate_mock_ohlcv(symbol, period="6mo")

    if df_full is None or df_full.empty:
        raise ValueError(f"No OHLCV data available for {symbol}")

    df_full = df_full.dropna(subset=["Close"])
    df_full = df_full.sort_index()

    total_rows = len(df_full)
    if total_rows < lookback_days + eval_window + 1:
        raise ValueError(
            f"Insufficient data for backtest: got {total_rows} rows, "
            f"need {lookback_days + eval_window + 1}."
        )

    # ── Walk-forward evaluation ───────────────────────────────────────────────
    # For each day in the eval window, compute signal on the lookback window
    # and check the next-day price change as ground truth.

    buy_tp = buy_fp = buy_tn = buy_fn = 0
    sell_tp = sell_fp = sell_tn = sell_fn = 0
    hold_count = 0

    daily_records = []

    eval_start = total_rows - eval_window - 1
    for i in range(eval_start, total_rows - 1):
        # Window: rows [i - lookback_days : i+1]
        window_start = max(0, i - lookback_days)
        df_window = df_full.iloc[window_start : i + 1].copy()

        if len(df_window) < 60:  # need enough rows for indicators
            continue

        date_str = str(df_full.index[i])[:10]
        current_price = float(df_full["Close"].iloc[i])
        next_price    = float(df_full["Close"].iloc[i + 1])
        fwd_return    = (next_price - current_price) / current_price

        # Ground truth
        actual_direction: str
        if fwd_return >= FORWARD_RETURN_THRESHOLD:
            actual_direction = "BUY"
        elif fwd_return <= -FORWARD_RETURN_THRESHOLD:
            actual_direction = "SELL"
        else:
            actual_direction = "HOLD"

        # Run signal engine on window
        try:
            df_ind = compute_indicators(df_window)
            signal = scan_for_signal(df_ind, symbol)
            predicted = signal["direction"] if signal else "HOLD"
        except Exception as exc:
            logger.debug("Signal error on %s: %s", date_str, exc)
            predicted = "HOLD"

        record = {
            "date": date_str,
            "current_price": round(current_price, 2),
            "next_price": round(next_price, 2),
            "fwd_return_pct": round(fwd_return * 100, 4),
            "predicted": predicted,
            "actual": actual_direction,
        }
        daily_records.append(record)

        # Accumulate BUY metrics
        if predicted == "BUY":
            if actual_direction == "BUY":
                buy_tp += 1
            else:
                buy_fp += 1
        else:
            if actual_direction == "BUY":
                buy_fn += 1
            else:
                buy_tn += 1

        # Accumulate SELL metrics
        if predicted == "SELL":
            if actual_direction == "SELL":
                sell_tp += 1
            else:
                sell_fp += 1
        else:
            if actual_direction == "SELL":
                sell_fn += 1
            else:
                sell_tn += 1

        if predicted == "HOLD":
            hold_count += 1

    n_signals = len(daily_records)
    buy_signals  = sum(1 for r in daily_records if r["predicted"] == "BUY")
    sell_signals = sum(1 for r in daily_records if r["predicted"] == "SELL")

    buy_precision  = _precision(buy_tp, buy_fp)
    buy_recall     = _recall(buy_tp, buy_fn)
    sell_precision = _precision(sell_tp, sell_fp)
    sell_recall    = _recall(sell_tp, sell_fn)

    report = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "eval_window_days": eval_window,
            "lookback_days": lookback_days,
            "forward_return_threshold_pct": FORWARD_RETURN_THRESHOLD * 100,
            "methodology": (
                "Walk-forward evaluation: for each day in the eval window, the signal engine "
                "runs on a rolling lookback window (no lookahead). Ground truth is determined "
                f"by the next-day price change: ≥{FORWARD_RETURN_THRESHOLD*100:.0f}% = BUY correct, "
                f"≤-{FORWARD_RETURN_THRESHOLD*100:.0f}% = SELL correct, otherwise HOLD."
            ),
            "indicator_config": {
                "ema_short": EMA_SHORT,
                "ema_long": EMA_LONG,
                "macd_fast": MACD_FAST,
                "macd_slow": MACD_SLOW,
                "macd_signal": MACD_SIGNAL_PERIOD,
                "rsi_oversold": RSI_OVERSOLD,
                "rsi_overbought": RSI_OVERBOUGHT,
            },
            "used_mock_data": use_mock_data,
        },
        "summary": {
            "total_days_evaluated": n_signals,
            "buy_signals_generated": buy_signals,
            "sell_signals_generated": sell_signals,
            "hold_signals_generated": hold_count,
        },
        "buy_metrics": {
            "true_positives": buy_tp,
            "false_positives": buy_fp,
            "true_negatives": buy_tn,
            "false_negatives": buy_fn,
            "precision": round(buy_precision, 4),
            "recall":    round(buy_recall, 4),
            "f1_score":  round(_f1(buy_precision, buy_recall), 4),
        },
        "sell_metrics": {
            "true_positives": sell_tp,
            "false_positives": sell_fp,
            "true_negatives": sell_tn,
            "false_negatives": sell_fn,
            "precision": round(sell_precision, 4),
            "recall":    round(sell_recall, 4),
            "f1_score":  round(_f1(sell_precision, sell_recall), 4),
        },
        "daily_records": daily_records,
    }

    # Save JSON
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(BACKTEST_JSON, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Backtest complete — saved to %s", BACKTEST_JSON)

    return report


def load_backtest_report() -> Optional[dict]:
    """Load the saved backtest report, or return None if it doesn't exist."""
    if not os.path.exists(BACKTEST_JSON):
        return None
    with open(BACKTEST_JSON) as f:
        return json.load(f)
