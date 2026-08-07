"""
Tests for XDI (Explainable Decision Inference) Engine
=====================================================
Validates that the XDI engine produces meaningful, structured
explanations grounded in actual indicator values.

Test categories:
    1. Output schema — all required keys present with correct types
    2. Content quality — explanations contain actual indicator values
    3. Signal-specific behaviour — BUY/SELL/HOLD produce appropriate content
    4. Risk assessment — risk levels and reasoning are consistent
    5. Confidence reasoning — dual confidence (rule + ML) explained separately
    6. Prediction horizon — data-driven from candle interval
    7. ML prediction — model-agnostic, prediction_type-driven, forecast features
    8. Pipeline integration — schema, confidence split, backward compatibility
"""

import os

import pytest

from ml.xdi.xdi_engine import XDIEngine
from ml.signals.signal_engine import SignalEngine
from ml.pipeline import run_analysis


# ==================================================================
# Fixtures
# ==================================================================
@pytest.fixture
def xdi():
    """Fresh XDIEngine instance."""
    return XDIEngine()


def _add_pipeline_metadata(signal_result, candle_interval="1day", ml_enabled=False):
    """Helper to attach pipeline metadata to a raw signal result."""
    signal_result["candle_interval"] = candle_interval
    signal_result["ml_prediction"] = {
        "enabled": ml_enabled,
        "prediction_type": None,
        "model": None,
        "predicted_price": None,
        "expected_change_percent": None,
        "prediction_confidence": None,
        "forecast_features": [],
    }
    signal_result["rule_confidence"] = signal_result["confidence"]
    signal_result["ml_confidence"] = None
    return signal_result


@pytest.fixture
def buy_signal(engine, buy_indicators):
    """Complete signal result for a BUY scenario (with pipeline metadata)."""
    return _add_pipeline_metadata(engine.generate_signal(buy_indicators))


@pytest.fixture
def sell_signal(engine, sell_indicators):
    """Complete signal result for a SELL scenario (with pipeline metadata)."""
    return _add_pipeline_metadata(engine.generate_signal(sell_indicators))


@pytest.fixture
def hold_signal(engine, hold_indicators):
    """Complete signal result for a HOLD scenario (with pipeline metadata)."""
    return _add_pipeline_metadata(engine.generate_signal(hold_indicators))


@pytest.fixture
def buy_signal_with_ml(engine, buy_indicators):
    """BUY signal with ML prediction enabled (simulates future model)."""
    result = engine.generate_signal(buy_indicators)
    result["candle_interval"] = "15min"
    result["ml_prediction"] = {
        "enabled": True,
        "prediction_type": "price_forecast",
        "model": "LSTM",
        "predicted_price": 175.50,
        "expected_change_percent": 2.1,
        "prediction_confidence": 0.79,
        "forecast_features": ["RSI", "MACD", "EMA20", "Volume"],
    }
    result["rule_confidence"] = result["confidence"]
    result["ml_confidence"] = 0.79
    # Simulate combined confidence (70% rule + 30% ml)
    result["confidence"] = round(
        0.70 * result["rule_confidence"] + 0.30 * 0.79, 4
    )
    return result


# ==================================================================
# Output Schema Tests
# ==================================================================
class TestXDIOutputSchema:
    """Validates the structure and types of XDI output."""

    REQUIRED_KEYS = {
        "summary",
        "detailed_reasoning",
        "key_factors",
        "risk_level",
        "risk_reasoning",
        "confidence_reasoning",
        "prediction_horizon",
        "actionable_insight",
        "timestamp",
    }

    REQUIRED_FACTOR_KEYS = {"indicator", "value", "interpretation", "impact"}

    REQUIRED_HORIZON_KEYS = {"display", "timeframe", "reasoning", "candle_interval"}

    def test_output_has_all_required_keys(self, xdi, buy_signal):
        """XDI output must contain all required top-level keys."""
        result = xdi.generate_explanation(buy_signal)
        assert self.REQUIRED_KEYS.issubset(set(result.keys())), (
            f"Missing keys: {self.REQUIRED_KEYS - set(result.keys())}"
        )

    def test_summary_is_nonempty_string(self, xdi, hold_signal):
        """Summary must be a non-empty string."""
        result = xdi.generate_explanation(hold_signal)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_detailed_reasoning_is_nonempty_string(self, xdi, buy_signal):
        """Detailed reasoning must be a non-empty string."""
        result = xdi.generate_explanation(buy_signal)
        assert isinstance(result["detailed_reasoning"], str)
        assert len(result["detailed_reasoning"]) > 50  # Must be substantive

    def test_key_factors_structure(self, xdi, sell_signal):
        """Each key factor must have indicator, value, interpretation, impact."""
        result = xdi.generate_explanation(sell_signal)
        factors = result["key_factors"]
        assert isinstance(factors, list)
        assert len(factors) == 4  # RSI, MACD, BB, EMA

        for factor in factors:
            assert self.REQUIRED_FACTOR_KEYS.issubset(factor.keys()), (
                f"Factor missing keys: {self.REQUIRED_FACTOR_KEYS - set(factor.keys())}"
            )

    def test_key_factor_impact_values(self, xdi, buy_signal):
        """Impact must be 'bullish', 'bearish', or 'neutral'."""
        result = xdi.generate_explanation(buy_signal)
        for factor in result["key_factors"]:
            assert factor["impact"] in {"bullish", "bearish", "neutral"}, (
                f"Invalid impact: {factor['impact']}"
            )

    def test_risk_level_validity(self, xdi, hold_signal):
        """Risk level must be LOW, MODERATE, HIGH, or EXTREME."""
        result = xdi.generate_explanation(hold_signal)
        assert result["risk_level"] in {"LOW", "MODERATE", "HIGH", "EXTREME"}

    def test_prediction_horizon_structure(self, xdi, buy_signal):
        """Prediction horizon must have display, timeframe, reasoning, candle_interval."""
        result = xdi.generate_explanation(buy_signal)
        horizon = result["prediction_horizon"]
        assert self.REQUIRED_HORIZON_KEYS.issubset(horizon.keys()), (
            f"Missing horizon keys: {self.REQUIRED_HORIZON_KEYS - set(horizon.keys())}"
        )

    def test_timestamp_present(self, xdi, hold_signal):
        """Timestamp must be a non-empty ISO-8601 string."""
        result = xdi.generate_explanation(hold_signal)
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]  # ISO-8601 format


# ==================================================================
# Content Quality Tests
# ==================================================================
class TestXDIContentQuality:
    """Validates that explanations reference actual indicator values."""

    def test_summary_contains_rsi_value(self, xdi, buy_signal):
        """Summary must reference the actual RSI value."""
        result = xdi.generate_explanation(buy_signal)
        rsi = buy_signal["indicators"]["rsi"]
        assert str(round(rsi, 1)) in result["summary"], (
            f"Summary does not contain RSI value {rsi:.1f}"
        )

    def test_summary_contains_close_price(self, xdi, sell_signal):
        """Summary must reference the actual close price."""
        result = xdi.generate_explanation(sell_signal)
        close = sell_signal["indicators"]["close"]
        assert f"{close:.2f}" in result["summary"], (
            f"Summary does not contain close price {close:.2f}"
        )

    def test_summary_contains_confidence(self, xdi, hold_signal):
        """Summary must reference the confidence percentage."""
        result = xdi.generate_explanation(hold_signal)
        assert "%" in result["summary"]

    def test_key_factors_contain_indicator_values(self, xdi, buy_signal):
        """Key factor interpretations must reference actual indicator values."""
        result = xdi.generate_explanation(buy_signal)
        indicators = buy_signal["indicators"]
        rsi_factor = result["key_factors"][0]  # RSI is always first
        assert str(round(indicators["rsi"], 1)) in rsi_factor["interpretation"]

    def test_detailed_reasoning_has_ta_section(self, xdi, sell_signal):
        """Detailed reasoning must contain a 'Technical Analysis' section."""
        result = xdi.generate_explanation(sell_signal)
        assert "Technical Analysis:" in result["detailed_reasoning"]

    def test_detailed_reasoning_has_overall_section(self, xdi, sell_signal):
        """Detailed reasoning must contain an 'Overall Recommendation' section."""
        result = xdi.generate_explanation(sell_signal)
        assert "Overall Recommendation:" in result["detailed_reasoning"]

    def test_actionable_insight_contains_price_levels(self, xdi, buy_signal):
        """Actionable insight for BUY/SELL must contain price levels."""
        result = xdi.generate_explanation(buy_signal)
        insight = result["actionable_insight"]
        assert "stop-loss" in insight.lower() or "stop" in insight.lower()


# ==================================================================
# Signal-Specific Behaviour Tests
# ==================================================================
class TestXDISignalBehaviour:
    """Validates signal-appropriate content generation."""

    def test_buy_summary_says_buy(self, xdi, buy_signal):
        result = xdi.generate_explanation(buy_signal)
        assert "BUY" in result["summary"]

    def test_sell_summary_says_sell(self, xdi, sell_signal):
        result = xdi.generate_explanation(sell_signal)
        assert "SELL" in result["summary"]

    def test_hold_summary_says_hold(self, xdi, hold_signal):
        result = xdi.generate_explanation(hold_signal)
        assert "HOLD" in result["summary"]

    def test_buy_has_bullish_factors(self, xdi, buy_signal):
        result = xdi.generate_explanation(buy_signal)
        bullish = [f for f in result["key_factors"] if f["impact"] == "bullish"]
        assert len(bullish) >= 1, "BUY signal has no bullish factors"

    def test_sell_has_bearish_factors(self, xdi, sell_signal):
        result = xdi.generate_explanation(sell_signal)
        bearish = [f for f in result["key_factors"] if f["impact"] == "bearish"]
        assert len(bearish) >= 1, "SELL signal has no bearish factors"

    def test_hold_actionable_says_no_action(self, xdi, hold_signal):
        result = xdi.generate_explanation(hold_signal)
        insight = result["actionable_insight"].lower()
        assert "no action" in insight or "monitor" in insight


# ==================================================================
# Risk Assessment Tests
# ==================================================================
class TestXDIRiskAssessment:
    """Validates risk level consistency."""

    def test_risk_reasoning_is_nonempty(self, xdi, buy_signal):
        result = xdi.generate_explanation(buy_signal)
        assert isinstance(result["risk_reasoning"], str)
        assert len(result["risk_reasoning"]) > 20

    def test_risk_reasoning_mentions_risk_level(self, xdi, sell_signal):
        result = xdi.generate_explanation(sell_signal)
        assert result["risk_level"] in result["risk_reasoning"]

    def test_low_confidence_elevates_risk(self, xdi, engine):
        mixed = {
            "rsi": 35.0,
            "ema_20": 180.00,
            "macd_line": -0.50,
            "macd_signal": 0.30,
            "macd_histogram": -0.80,
            "bb_upper": 185.00,
            "bb_middle": 180.00,
            "bb_lower": 178.00,
            "close": 176.00,
        }
        signal = engine.generate_signal(mixed)
        _add_pipeline_metadata(signal)
        result = xdi.generate_explanation(signal)
        assert result["risk_level"] in {"MODERATE", "HIGH", "EXTREME"}, (
            f"Expected elevated risk, got {result['risk_level']} "
            f"with confidence={signal['confidence']}"
        )


# ==================================================================
# Confidence Reasoning Tests (Dual Confidence)
# ==================================================================
class TestXDIConfidenceReasoning:
    """Validates confidence explanation, including dual-source confidence."""

    def test_confidence_reasoning_is_nonempty(self, xdi, hold_signal):
        result = xdi.generate_explanation(hold_signal)
        assert isinstance(result["confidence_reasoning"], str)
        assert len(result["confidence_reasoning"]) > 20

    def test_confidence_reasoning_mentions_percentage(self, xdi, buy_signal):
        result = xdi.generate_explanation(buy_signal)
        assert "%" in result["confidence_reasoning"]

    def test_dual_confidence_explained_when_ml_active(self, xdi, buy_signal_with_ml):
        """When ML is active, confidence reasoning must mention both sources."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["confidence_reasoning"]
        assert "rule confidence" in reasoning.lower() or "rule" in reasoning.lower()

    def test_dual_confidence_not_mentioned_when_ml_disabled(self, xdi, buy_signal):
        """When ML is disabled, confidence reasoning should not mention dual sources."""
        result = xdi.generate_explanation(buy_signal)
        reasoning = result["confidence_reasoning"]
        # Should not have the dual confidence language
        assert "price forecast has" not in reasoning.lower()


# ==================================================================
# Prediction Horizon Tests (data-driven from candle interval)
# ==================================================================
class TestXDIPredictionHorizon:
    """Validates that prediction horizon is driven by candle interval."""

    def test_1day_horizon(self, xdi, engine, buy_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(buy_indicators), candle_interval="1day"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "5–10" in horizon["display"]
        assert horizon["timeframe"] == "medium-term"
        assert horizon["candle_interval"] == "1day"

    def test_15min_horizon(self, xdi, engine, hold_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(hold_indicators), candle_interval="15min"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "1–4 hours" in horizon["display"]
        assert horizon["timeframe"] == "intraday"
        assert horizon["candle_interval"] == "15min"

    def test_1min_horizon(self, xdi, engine, sell_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(sell_indicators), candle_interval="1min"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "5–15 minutes" in horizon["display"]
        assert horizon["timeframe"] == "intraday"

    def test_5min_horizon(self, xdi, engine, buy_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(buy_indicators), candle_interval="5min"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "30–60 minutes" in horizon["display"]

    def test_1hour_horizon(self, xdi, engine, hold_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(hold_indicators), candle_interval="1hour"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "trading day" in horizon["display"]
        assert horizon["timeframe"] == "short-term"

    def test_horizon_reasoning_references_candle_interval(self, xdi, engine, buy_indicators):
        signal = _add_pipeline_metadata(
            engine.generate_signal(buy_indicators), candle_interval="15min"
        )
        result = xdi.generate_explanation(signal)
        horizon = result["prediction_horizon"]
        assert "15-minute" in horizon["reasoning"] or "15 minute" in horizon["reasoning"]


# ==================================================================
# ML Prediction Tests (model-agnostic + forecast features)
# ==================================================================
class TestXDIMLPrediction:
    """Validates model-agnostic ML prediction behaviour."""

    def test_ml_disabled_no_ml_section(self, xdi, buy_signal):
        """When ML is disabled, detailed reasoning must NOT have ML section."""
        result = xdi.generate_explanation(buy_signal)
        assert "Machine Learning Forecast:" not in result["detailed_reasoning"]

    def test_ml_enabled_includes_ml_section(self, xdi, buy_signal_with_ml):
        """When ML is enabled, detailed reasoning MUST have ML section."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        assert "Machine Learning Forecast:" in result["detailed_reasoning"]

    def test_ml_uses_prediction_type_not_model_name_in_description(self, xdi, buy_signal_with_ml):
        """ML section should describe the prediction type, not lead with model name."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["detailed_reasoning"]
        # Should use "price forecast model" (from prediction_type), not lead with "LSTM"
        assert "price forecast model" in reasoning

    def test_ml_model_name_mentioned_as_metadata(self, xdi, buy_signal_with_ml):
        """Model name should still appear, but as metadata, not as primary description."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["detailed_reasoning"]
        assert "Model: LSTM" in reasoning

    def test_ml_mentions_predicted_price(self, xdi, buy_signal_with_ml):
        result = xdi.generate_explanation(buy_signal_with_ml)
        assert "175.50" in result["detailed_reasoning"]

    def test_ml_mentions_change_percent(self, xdi, buy_signal_with_ml):
        result = xdi.generate_explanation(buy_signal_with_ml)
        assert "2.1%" in result["detailed_reasoning"]

    def test_ml_mentions_prediction_confidence(self, xdi, buy_signal_with_ml):
        """ML section should mention the prediction's own confidence."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["detailed_reasoning"]
        assert "79%" in reasoning or "Forecast confidence" in reasoning

    def test_ml_mentions_forecast_features(self, xdi, buy_signal_with_ml):
        """ML section should list the features used for the forecast."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["detailed_reasoning"]
        assert "RSI" in reasoning
        assert "MACD" in reasoning
        assert "Volume" in reasoning
        assert "Based on:" in reasoning

    def test_ml_section_respects_horizon(self, xdi, buy_signal_with_ml):
        """ML section should reference the prediction horizon display."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        assert "1–4 hours" in result["detailed_reasoning"]

    def test_overall_shows_dual_confidence_breakdown(self, xdi, buy_signal_with_ml):
        """Overall section should show rule + ML confidence breakdown."""
        result = xdi.generate_explanation(buy_signal_with_ml)
        reasoning = result["detailed_reasoning"]
        assert "Confidence breakdown:" in reasoning
        assert "rule engine" in reasoning
        assert "ML forecast" in reasoning

    def test_model_agnostic_with_gru(self, xdi, engine, buy_indicators):
        """XDI should work identically with a different model name (GRU)."""
        result = engine.generate_signal(buy_indicators)
        result["candle_interval"] = "5min"
        result["ml_prediction"] = {
            "enabled": True,
            "prediction_type": "price_forecast",
            "model": "GRU",
            "predicted_price": 174.00,
            "expected_change_percent": 1.2,
            "prediction_confidence": 0.65,
            "forecast_features": ["RSI", "Close"],
        }
        result["rule_confidence"] = result["confidence"]
        result["ml_confidence"] = 0.65
        result["confidence"] = round(0.70 * result["rule_confidence"] + 0.30 * 0.65, 4)

        explanation = xdi.generate_explanation(result)
        reasoning = explanation["detailed_reasoning"]
        # Uses prediction_type description, not model name
        assert "price forecast model" in reasoning
        # Model name as metadata
        assert "Model: GRU" in reasoning
        # Features listed
        assert "RSI" in reasoning and "Close" in reasoning


# ==================================================================
# Pipeline Integration Tests
# ==================================================================
class TestXDIPipelineIntegration:
    """Validates XDI integrates correctly with the full pipeline."""

    def test_pipeline_includes_explanation(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)

        assert "explanation" in result
        explanation = result["explanation"]

        required_keys = {
            "summary", "detailed_reasoning", "key_factors",
            "risk_level", "risk_reasoning", "confidence_reasoning",
            "prediction_horizon", "actionable_insight", "timestamp",
        }
        assert required_keys.issubset(explanation.keys())
        assert result["signal"] in explanation["summary"]
        assert len(explanation["key_factors"]) == 4

    def test_pipeline_includes_ml_prediction_stub(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)

        assert "ml_prediction" in result
        ml = result["ml_prediction"]
        assert ml["enabled"] is False
        assert ml["prediction_type"] is None
        assert ml["model"] is None
        assert ml["predicted_price"] is None
        assert ml["expected_change_percent"] is None
        assert ml["prediction_confidence"] is None
        assert ml["forecast_features"] == []

    def test_pipeline_has_dual_confidence(self):
        """Pipeline must output rule_confidence, ml_confidence, and combined confidence."""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)

        assert "rule_confidence" in result
        assert "ml_confidence" in result
        assert "confidence" in result
        # When ML disabled: confidence == rule_confidence, ml_confidence is None
        assert result["ml_confidence"] is None
        assert result["confidence"] == result["rule_confidence"]
        assert 0.0 <= result["rule_confidence"] <= 1.0

    def test_pipeline_includes_candle_interval(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)
        assert result["candle_interval"] == "1day"

    def test_pipeline_custom_candle_interval(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path, candle_interval="15min")
        assert result["candle_interval"] == "15min"
        horizon = result["explanation"]["prediction_horizon"]
        assert "1–4 hours" in horizon["display"]

    def test_pipeline_invalid_candle_interval_raises(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        with pytest.raises(ValueError, match="Invalid candle_interval"):
            run_analysis(source="csv", filepath=csv_path, candle_interval="3min")

    def test_pipeline_xdi_does_not_break_existing_output(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "sample_ohlcv.csv",
        )
        result = run_analysis(source="csv", filepath=csv_path)

        # All original keys must still exist
        assert "signal" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert "indicators" in result
        assert "rules_triggered" in result
        assert "source" in result

        # Original values must still be valid
        assert result["signal"] in {"BUY", "SELL", "HOLD"}
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["source"] == "csv"
