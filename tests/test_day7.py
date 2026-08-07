"""
Day 7 Unit Tests — Hybrid Decision Engine & Pipeline Integration

Tests cover:
    - HybridDecisionEngine agreement classification
    - Direction mapping (signal → direction, change% → direction)
    - Final signal resolution (CONFLICT → HOLD)
    - Reasoning string generation
    - Pipeline integration (hybrid_decision in result dict)
    - XDI engine: summary and reasoning with agreement context
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# HybridDecisionEngine tests
# ============================================================

class TestHybridDecisionEngine:

    def _engine(self):
        from ml.decision.hybrid_decision_engine import HybridDecisionEngine
        return HybridDecisionEngine()

    def _ml_disabled(self):
        return {"enabled": False, "expected_change_percent": None, "prediction_confidence": None}

    def _ml_up(self, pct=1.5, conf=0.80):
        return {
            "enabled": True,
            "expected_change_percent": pct,
            "prediction_confidence": conf,
        }

    def _ml_down(self, pct=-1.5, conf=0.80):
        return {
            "enabled": True,
            "expected_change_percent": pct,
            "prediction_confidence": conf,
        }

    def _ml_neutral(self):
        return {
            "enabled": True,
            "expected_change_percent": 0.0,  # below threshold → neutral
            "prediction_confidence": 0.70,
        }

    def _signal(self, sig, conf=0.82):
        return {"signal": sig, "rule_confidence": conf, "confidence": conf}

    # --- Agreement tests ---

    def test_strong_agreement_buy_up(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY", 0.85), self._ml_up(1.5, 0.80))
        assert result["agreement"] == "STRONG_AGREEMENT"
        assert result["final_signal"] == "BUY"

    def test_strong_agreement_sell_down(self):
        engine = self._engine()
        result = engine.combine(self._signal("SELL", 0.85), self._ml_down(-1.5, 0.80))
        assert result["agreement"] == "STRONG_AGREEMENT"
        assert result["final_signal"] == "SELL"

    def test_partial_agreement_low_ml_conf(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY", 0.85), self._ml_up(1.5, 0.50))
        assert result["agreement"] == "PARTIAL_AGREEMENT"
        assert result["final_signal"] == "BUY"

    def test_conflict_buy_ml_down(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_down(-2.0, 0.80))
        assert result["agreement"] == "CONFLICT"
        assert result["final_signal"] == "HOLD"

    def test_conflict_sell_ml_up(self):
        engine = self._engine()
        result = engine.combine(self._signal("SELL"), self._ml_up(2.0, 0.80))
        assert result["agreement"] == "CONFLICT"
        assert result["final_signal"] == "HOLD"

    def test_neutral_ml_disabled(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_disabled())
        assert result["agreement"] == "NEUTRAL"
        assert result["final_signal"] == "BUY"

    def test_neutral_technical_hold(self):
        engine = self._engine()
        result = engine.combine(self._signal("HOLD"), self._ml_up())
        assert result["agreement"] == "NEUTRAL"
        assert result["final_signal"] == "HOLD"

    def test_neutral_ml_change_below_threshold(self):
        """ML change% ≤ threshold → ML direction is NEUTRAL → NEUTRAL agreement."""
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_neutral())
        assert result["agreement"] == "NEUTRAL"

    # --- Output schema tests ---

    def test_output_schema(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_up())
        expected_keys = {
            "final_signal", "agreement",
            "technical_signal", "ml_direction", "reasoning",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_technical_signal_block(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY", 0.82), self._ml_up())
        ts = result["technical_signal"]
        assert ts["signal"] == "BUY"
        assert ts["confidence"] == pytest.approx(0.82, abs=1e-4)
        assert ts["direction"] == "UP"

    def test_ml_direction_block(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_up(2.5, 0.75))
        ml = result["ml_direction"]
        assert ml["enabled"] is True
        assert ml["direction"] == "UP"
        assert ml["change_pct"] == pytest.approx(2.5, abs=1e-2)
        assert ml["confidence"] == pytest.approx(0.75, abs=1e-4)

    def test_ml_direction_disabled(self):
        engine = self._engine()
        result = engine.combine(self._signal("SELL"), self._ml_disabled())
        ml = result["ml_direction"]
        assert ml["enabled"] is False
        assert ml["direction"] == "NEUTRAL"
        assert ml["change_pct"] is None

    # --- Reasoning tests ---

    def test_reasoning_mentions_signal(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_up())
        assert "BUY" in result["reasoning"]

    def test_conflict_reasoning_mentions_hold(self):
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), self._ml_down())
        assert "HOLD" in result["reasoning"] or "conflict" in result["reasoning"].lower()

    def test_disabled_ml_reasoning(self):
        engine = self._engine()
        result = engine.combine(self._signal("SELL"), self._ml_disabled())
        assert "not yet active" in result["reasoning"].lower() or "disabled" in result["reasoning"].lower() or "ML" in result["reasoning"]

    # --- Edge cases ---

    def test_combine_with_none_ml(self):
        """combine(signal, None) should work gracefully."""
        engine = self._engine()
        result = engine.combine(self._signal("BUY"), None)
        assert result["agreement"] == "NEUTRAL"
        assert result["final_signal"] == "BUY"

    def test_combine_reads_ml_from_signal_result(self):
        """combine() also reads ml_prediction from signal_result if no separate arg."""
        engine = self._engine()
        sig = self._signal("BUY")
        sig["ml_prediction"] = self._ml_up()
        result = engine.combine(sig, None)
        # ML is taken from signal_result["ml_prediction"]
        assert result["agreement"] in ("STRONG_AGREEMENT", "PARTIAL_AGREEMENT", "NEUTRAL")


# ============================================================
# Pipeline integration tests (no TF required — ML disabled path)
# ============================================================

class TestPipelineIntegration:
    """
    Integration tests for the pipeline with the hybrid decision.
    Uses the CSV source with sample data to avoid network calls.
    ML prediction remains disabled (no trained model exists).
    """

    SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")),
        reason="sample_ohlcv.csv not found",
    )
    def test_pipeline_result_has_hybrid_decision(self):
        from ml.pipeline import run_analysis
        result = run_analysis(source="csv", filepath=self.SAMPLE_CSV)
        assert "hybrid_decision" in result
        hd = result["hybrid_decision"]
        assert "final_signal" in hd
        assert "agreement" in hd
        assert "reasoning" in hd
        assert hd["final_signal"] in ("BUY", "SELL", "HOLD")

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")),
        reason="sample_ohlcv.csv not found",
    )
    def test_pipeline_has_validity_fields(self):
        from ml.pipeline import run_analysis
        result = run_analysis(source="csv", filepath=self.SAMPLE_CSV)
        assert "generated_at" in result
        assert "data_as_of" in result
        assert "prediction_horizon" in result

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")),
        reason="sample_ohlcv.csv not found",
    )
    def test_ml_prediction_disabled_schema(self):
        from ml.pipeline import run_analysis
        result = run_analysis(source="csv", filepath=self.SAMPLE_CSV)
        ml = result["ml_prediction"]
        assert ml["enabled"] is False
        assert ml["predicted_price"] is None

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")),
        reason="sample_ohlcv.csv not found",
    )
    def test_pipeline_with_ml_disabled_neutral_agreement(self):
        from ml.pipeline import run_analysis
        result = run_analysis(source="csv", filepath=self.SAMPLE_CSV)
        assert result["hybrid_decision"]["agreement"] == "NEUTRAL"


# ============================================================
# XDI Engine — agreement-aware explanation tests
# ============================================================

class TestXDIWithAgreement:
    """Test that XDI engine produces grounded explanations using hybrid_decision."""

    def _make_signal_result(
        self, signal="BUY", agreement="NEUTRAL", ml_enabled=False, change_pct=None
    ):
        ml_prediction = {
            "enabled": ml_enabled,
            "prediction_type": "price_forecast" if ml_enabled else None,
            "model": "LSTM" if ml_enabled else None,
            "predicted_price": 192.0 if ml_enabled else None,
            "expected_change_percent": change_pct,
            "prediction_confidence": 0.78 if ml_enabled else None,
            "prediction_horizon": "next trading day",
            "forecast_features": [],
        }
        return {
            "signal": signal,
            "confidence": 0.82,
            "rule_confidence": 0.82,
            "indicators": {
                "rsi": 28.0,
                "ema_20": 185.0,
                "macd_line": 0.012,
                "macd_signal": 0.008,
                "macd_histogram": 0.004,
                "bb_upper": 200.0,
                "bb_middle": 190.0,
                "bb_lower": 180.0,
                "close": 181.0,
            },
            "rules_triggered": ["RSI oversold < 30"],
            "candle_interval": "1day",
            "ml_prediction": ml_prediction,
            "hybrid_decision": {
                "final_signal": "HOLD" if agreement == "CONFLICT" else signal,
                "agreement": agreement,
                "reasoning": "test reasoning",
            },
        }

    def test_agreement_field_in_output(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result()
        explanation = xdi.generate_explanation(signal_result)
        assert "agreement" in explanation
        assert explanation["agreement"] == "NEUTRAL"

    def test_neutral_agreement_summary_normal(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result("BUY", "NEUTRAL", False)
        explanation = xdi.generate_explanation(signal_result)
        assert "BUY" in explanation["summary"]

    def test_strong_agreement_summary_mentions_both(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result(
            "BUY", "STRONG_AGREEMENT", True, change_pct=2.1
        )
        explanation = xdi.generate_explanation(signal_result)
        # Should mention both BUY and ML forecast
        summary = explanation["summary"]
        assert "BUY" in summary
        assert "2.1" in summary or "LSTM" in summary or "forecast" in summary.lower()

    def test_conflict_summary_mentions_hold(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result(
            "BUY", "CONFLICT", True, change_pct=-2.5
        )
        explanation = xdi.generate_explanation(signal_result)
        # Signal should be overridden to HOLD with conflict explanation
        summary = explanation["summary"]
        assert "HOLD" in summary or "conflict" in summary.lower()

    def test_detailed_reasoning_has_agreement_note(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result(
            "BUY", "STRONG_AGREEMENT", True, change_pct=1.8
        )
        explanation = xdi.generate_explanation(signal_result)
        reasoning = explanation["detailed_reasoning"]
        # Should have the agreement annotation in Overall Recommendation section
        assert "Strong agreement" in reasoning or "agreement" in reasoning.lower()

    def test_all_existing_xdi_fields_present(self):
        from ml.xdi.xdi_engine import XDIEngine
        xdi = XDIEngine()
        signal_result = self._make_signal_result()
        explanation = xdi.generate_explanation(signal_result)
        required_keys = {
            "summary", "detailed_reasoning", "key_factors",
            "risk_level", "risk_reasoning", "confidence_reasoning",
            "prediction_horizon", "actionable_insight", "timestamp",
            "agreement",
        }
        assert required_keys.issubset(set(explanation.keys()))


# ============================================================
# _disabled_ml_placeholder and _candle_horizon_label tests
# ============================================================

class TestPipelineHelpers:

    def test_disabled_ml_placeholder_schema(self):
        from ml.pipeline import _disabled_ml_placeholder
        placeholder = _disabled_ml_placeholder()
        assert placeholder["enabled"] is False
        assert placeholder["predicted_price"] is None
        assert placeholder["forecast_features"] == []

    def test_candle_horizon_label(self):
        from ml.pipeline import _candle_horizon_label
        assert "minute" in _candle_horizon_label("1min") or "min" in _candle_horizon_label("1min")
        assert "day" in _candle_horizon_label("1day")
        assert "trading" in _candle_horizon_label("1day")
