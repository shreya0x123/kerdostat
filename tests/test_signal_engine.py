"""
Tests for Signal Engine
=======================
Validates signal generation logic, output schema, confidence scoring,
and end-to-end pipeline integration.

These tests ensure the SignalEngine output contract is stable for
Day 3's XDI (Explainable Decision Inference) engine consumption.
"""

import os

import pytest

from ml.signals.signal_engine import SignalEngine
from ml.pipeline import run_analysis


# ==================================================================
# Signal Generation Tests
# ==================================================================
class TestSignalGeneration:
    """Tests for BUY / SELL / HOLD signal logic."""

    def test_buy_signal(self, engine, buy_indicators):
        """Oversold RSI + bullish MACD + price below BB lower → BUY."""
        result = engine.generate_signal(buy_indicators)
        assert result["signal"] == "BUY", (
            f"Expected BUY, got {result['signal']} "
            f"with RSI={buy_indicators['rsi']}"
        )

    def test_sell_signal(self, engine, sell_indicators):
        """Overbought RSI + bearish MACD + price above BB upper → SELL."""
        result = engine.generate_signal(sell_indicators)
        assert result["signal"] == "SELL", (
            f"Expected SELL, got {result['signal']} "
            f"with RSI={sell_indicators['rsi']}"
        )

    def test_hold_signal(self, engine, hold_indicators):
        """Neutral RSI + mixed indicators → HOLD."""
        result = engine.generate_signal(hold_indicators)
        assert result["signal"] == "HOLD", (
            f"Expected HOLD, got {result['signal']} "
            f"with RSI={hold_indicators['rsi']}"
        )


# ==================================================================
# Output Schema Tests
# ==================================================================
class TestOutputSchema:
    """Tests for the structure and types of signal engine output."""

    REQUIRED_TOP_KEYS = {"signal", "confidence", "timestamp", "indicators", "rules_triggered"}

    REQUIRED_INDICATOR_KEYS = {
        "rsi", "ema_20", "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_middle", "bb_lower", "close",
    }

    def test_output_has_required_keys(self, engine, hold_indicators):
        """Signal output must contain all required top-level keys."""
        result = engine.generate_signal(hold_indicators)
        assert self.REQUIRED_TOP_KEYS.issubset(result.keys()), (
            f"Missing keys: {self.REQUIRED_TOP_KEYS - set(result.keys())}"
        )

    def test_signal_validity(self, engine, hold_indicators):
        """Signal value must be one of BUY, SELL, or HOLD."""
        result = engine.generate_signal(hold_indicators)
        assert result["signal"] in {"BUY", "SELL", "HOLD"}, (
            f"Invalid signal: {result['signal']}"
        )

    def test_confidence_range(self, engine, buy_indicators):
        """Confidence must be in the range [0.0, 1.0]."""
        result = engine.generate_signal(buy_indicators)
        assert 0.0 <= result["confidence"] <= 1.0, (
            f"Confidence {result['confidence']} is out of range [0.0, 1.0]"
        )

    def test_indicators_passthrough(self, engine, buy_indicators):
        """The indicators dict should be passed through unchanged."""
        result = engine.generate_signal(buy_indicators)
        assert self.REQUIRED_INDICATOR_KEYS.issubset(result["indicators"].keys()), (
            f"Missing indicator keys in output"
        )

    def test_rules_triggered_nonempty_for_buy_sell(self, engine, buy_indicators, sell_indicators):
        """BUY and SELL signals must always have at least one rule triggered."""
        buy_result = engine.generate_signal(buy_indicators)
        assert len(buy_result["rules_triggered"]) > 0, (
            "BUY signal has no rules_triggered"
        )

        sell_result = engine.generate_signal(sell_indicators)
        assert len(sell_result["rules_triggered"]) > 0, (
            "SELL signal has no rules_triggered"
        )


# ==================================================================
# End-to-End Pipeline Test
# ==================================================================
class TestPipelineIntegration:
    """Tests for the full pipeline from CSV → signal output."""

    def test_full_pipeline_csv(self):
        """run_analysis with CSV source should return a valid signal dict."""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)

        # Validate structure
        assert "signal" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert "indicators" in result
        assert "rules_triggered" in result
        assert "source" in result
        assert "candle_interval" in result
        assert "ml_prediction" in result
        assert "explanation" in result

        # Validate values
        assert result["signal"] in {"BUY", "SELL", "HOLD"}
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["source"] == "csv"
        assert isinstance(result["rules_triggered"], list)
        assert result["candle_interval"] == "1day"
        assert result["ml_prediction"]["enabled"] is False