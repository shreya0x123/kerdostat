"""
Kerdostat ML Decision — Hybrid Decision Engine (Day 7)
=======================================================
Combines the technical rule-based signal with the LSTM price forecast
to produce a final hybrid recommendation.

Architecture:
    Technical Signal (BUY/SELL/HOLD + confidence)
           +
    LSTM Price Forecast (expected_change_percent)
           ↓
    HybridDecisionEngine.combine()
           ↓
    {
        "final_signal": "BUY",
        "agreement": "STRONG_AGREEMENT",
        "technical_signal": {...},
        "ml_prediction": {"direction": "UP", "change_pct": 2.1},
        "reasoning": "...",
    }

Agreement classification:
    STRONG_AGREEMENT  — both sources point the same direction, both high confidence
    PARTIAL_AGREEMENT — same direction, but at least one has low confidence
    NEUTRAL           — HOLD signal or ML disabled / no prediction
    CONFLICT          — technical and ML point opposite directions

The hybrid engine is TRANSPARENT AND DETERMINISTIC. It never invents
reasons — every output field is derived from actual pipeline values.
It does NOT override the signal engine's BUY/SELL/HOLD decision. It
enriches the output with an agreement assessment that the XDI engine
uses to generate grounded explanations.

Usage:
    from ml.decision.hybrid_decision_engine import HybridDecisionEngine

    engine = HybridDecisionEngine()
    hybrid = engine.combine(signal_result, ml_prediction)
    print(hybrid["agreement"])   # "STRONG_AGREEMENT"
    print(hybrid["final_signal"])  # "BUY"
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Agreement(str, Enum):
    """Level of agreement between technical and ML signals."""
    STRONG_AGREEMENT  = "STRONG_AGREEMENT"
    PARTIAL_AGREEMENT = "PARTIAL_AGREEMENT"
    NEUTRAL           = "NEUTRAL"
    CONFLICT          = "CONFLICT"


class Direction(str, Enum):
    """Directional expectation derived from a signal or forecast."""
    UP      = "UP"
    DOWN    = "DOWN"
    NEUTRAL = "NEUTRAL"


# Thresholds (transparent, documented)
CHANGE_PCT_THRESHOLD  = 0.3   # |change%| below this is treated as NEUTRAL
HIGH_CONFIDENCE_FLOOR = 0.60  # confidence >= this is "high"


class HybridDecisionEngine:
    """
    Combines technical-analysis signal with LSTM price forecast.

    The engine:
    1. Derives a directional expectation from the technical signal.
    2. Derives a directional expectation from the ML price forecast.
    3. Classifies agreement between the two.
    4. Produces a final recommendation and a one-sentence reasoning string.

    The engine NEVER silently replaces the technical signal. When there
    is a CONFLICT, the final_signal defaults to HOLD (safe behaviour).
    When the ML model is disabled, the final_signal mirrors the technical
    signal unchanged.
    """

    def combine(
        self,
        signal_result: dict,
        ml_prediction: Optional[dict] = None,
    ) -> dict:
        """
        Produce the hybrid decision output.

        Args:
            signal_result:  Dict from SignalEngine (contains signal, confidence, …).
            ml_prediction:  Dict from LSTMPredictor (may be None or enabled=False).

        Returns:
            dict with keys:
                final_signal      — "BUY" | "SELL" | "HOLD"
                agreement         — Agreement enum value (string)
                technical_signal  — {"signal": ..., "confidence": ...}
                ml_direction      — {"direction": ..., "change_pct": ..., "enabled": bool}
                reasoning         — one-sentence human-readable explanation
        """
        tech_signal    = signal_result.get("signal", "HOLD")
        tech_confidence = signal_result.get("rule_confidence",
                                            signal_result.get("confidence", 0.5))
        ml_pred        = ml_prediction or signal_result.get("ml_prediction") or {}
        ml_enabled     = bool(ml_pred.get("enabled", False))

        # --- Derive directions ---
        tech_dir = self._signal_to_direction(tech_signal)
        ml_dir, change_pct = self._forecast_to_direction(ml_pred, ml_enabled)
        ml_conf = ml_pred.get("prediction_confidence") if ml_enabled else None

        # --- Classify agreement ---
        agreement = self._classify_agreement(
            tech_dir, ml_dir, tech_confidence, ml_conf, ml_enabled
        )

        # --- Final signal ---
        final_signal = self._resolve_final_signal(tech_signal, agreement)

        # --- Reasoning ---
        reasoning = self._build_reasoning(
            tech_signal, tech_confidence, tech_dir,
            ml_dir, change_pct, ml_conf, agreement, ml_enabled,
        )

        logger.info(
            "HybridDecision: tech=%s(%s) ml=%s(%.1f%%) → %s [%s]",
            tech_signal, f"{tech_confidence:.0%}",
            ml_dir.value, change_pct or 0,
            final_signal, agreement.value,
        )

        return {
            "final_signal": final_signal,
            "agreement": agreement.value,
            "technical_signal": {
                "signal":     tech_signal,
                "confidence": round(tech_confidence, 4),
                "direction":  tech_dir.value,
            },
            "ml_direction": {
                "enabled":    ml_enabled,
                "direction":  ml_dir.value,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "confidence": round(ml_conf, 4) if ml_conf is not None else None,
            },
            "reasoning": reasoning,
        }

    # ------------------------------------------------------------------
    # Direction mapping
    # ------------------------------------------------------------------
    @staticmethod
    def _signal_to_direction(signal: str) -> Direction:
        """Map BUY/SELL/HOLD to a directional expectation."""
        if signal == "BUY":
            return Direction.UP
        if signal == "SELL":
            return Direction.DOWN
        return Direction.NEUTRAL

    @staticmethod
    def _forecast_to_direction(
        ml_pred: dict, enabled: bool
    ) -> tuple[Direction, Optional[float]]:
        """
        Derive directional expectation from ML price forecast.

        Returns (direction, change_pct).
        """
        if not enabled:
            return Direction.NEUTRAL, None

        change_pct = ml_pred.get("expected_change_percent")
        if change_pct is None:
            return Direction.NEUTRAL, None

        if change_pct > CHANGE_PCT_THRESHOLD:
            return Direction.UP, change_pct
        if change_pct < -CHANGE_PCT_THRESHOLD:
            return Direction.DOWN, change_pct
        return Direction.NEUTRAL, change_pct

    # ------------------------------------------------------------------
    # Agreement classification
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_agreement(
        tech_dir: Direction,
        ml_dir: Direction,
        tech_confidence: float,
        ml_confidence: Optional[float],
        ml_enabled: bool,
    ) -> Agreement:
        """
        Classify the agreement level between technical and ML signals.

        Logic (transparent and deterministic):
            1. ML disabled or neutral → NEUTRAL
            2. Technical HOLD → NEUTRAL
            3. Same direction + both high confidence → STRONG_AGREEMENT
            4. Same direction + at least one low confidence → PARTIAL_AGREEMENT
            5. Opposite directions → CONFLICT
        """
        if not ml_enabled or ml_dir == Direction.NEUTRAL:
            return Agreement.NEUTRAL

        if tech_dir == Direction.NEUTRAL:
            return Agreement.NEUTRAL

        if tech_dir == ml_dir:
            both_high = (
                tech_confidence >= HIGH_CONFIDENCE_FLOOR
                and (ml_confidence is None or ml_confidence >= HIGH_CONFIDENCE_FLOOR)
            )
            return Agreement.STRONG_AGREEMENT if both_high else Agreement.PARTIAL_AGREEMENT

        # Directions are opposite
        return Agreement.CONFLICT

    # ------------------------------------------------------------------
    # Final signal resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_final_signal(tech_signal: str, agreement: Agreement) -> str:
        """
        Determine the final output signal.

        Policy:
            - CONFLICT → HOLD  (preserve capital, reduce risk)
            - Otherwise → follow the technical signal
              (ML enriches; it does not override the rules engine)
        """
        if agreement == Agreement.CONFLICT:
            return "HOLD"
        return tech_signal

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------
    @staticmethod
    def _build_reasoning(
        tech_signal: str,
        tech_confidence: float,
        tech_dir: Direction,
        ml_dir: Direction,
        change_pct: Optional[float],
        ml_confidence: Optional[float],
        agreement: Agreement,
        ml_enabled: bool,
    ) -> str:
        """Build a single, grounded sentence explaining the hybrid decision."""

        if not ml_enabled:
            return (
                f"Technical analysis recommends {tech_signal} with "
                f"{tech_confidence:.0%} confidence. ML prediction is not yet active."
            )

        change_str = (
            f"{'+' if change_pct and change_pct > 0 else ''}{change_pct:.1f}%"
            if change_pct is not None else "neutral"
        )
        ml_dir_label = ml_dir.value.lower() if ml_dir != Direction.NEUTRAL else "neutral"
        ml_conf_str = (
            f" ({ml_confidence:.0%} ML confidence)"
            if ml_confidence is not None else ""
        )

        if agreement == Agreement.STRONG_AGREEMENT:
            return (
                f"Both technical analysis ({tech_signal}, {tech_confidence:.0%} confidence) "
                f"and LSTM forecast ({change_str} expected{ml_conf_str}) point {ml_dir_label}. "
                f"Strong agreement supports the {tech_signal} signal."
            )

        if agreement == Agreement.PARTIAL_AGREEMENT:
            return (
                f"Technical analysis suggests {tech_signal} and LSTM forecasts a "
                f"{change_str} move — same direction, but confidence is moderate. "
                f"Partial agreement: proceed with caution."
            )

        if agreement == Agreement.CONFLICT:
            return (
                f"Technical analysis signals {tech_signal} but the LSTM forecasts "
                f"a {change_str} move in the opposite direction. "
                f"Conflicting evidence → HOLD recommended."
            )

        # NEUTRAL
        return (
            f"Technical analysis recommends {tech_signal} ({tech_confidence:.0%} confidence). "
            f"LSTM forecast is neutral (expected change: {change_str}). "
            f"No directional conflict detected."
        )
