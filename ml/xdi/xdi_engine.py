"""
Kerdostat XDI (Explainable Decision Inference) Engine
=====================================================
Generates human-readable, natural-language justifications for every
trading signal produced by the SignalEngine.

The XDI engine transforms raw indicator values and triggered rules
into structured explanations that give traders transparency into
*why* a particular signal was generated — shifting the system from
Black Box to Glass Box decision-making.

Architecture:
    SignalEngine output → XDI Engine → Enriched output with:
        - summary:              One-sentence human-readable verdict
        - detailed_reasoning:   Sectioned analysis (TA + ML forecast + overall)
        - key_factors:          List of the most influential factors
        - risk_level:           LOW / MODERATE / HIGH / EXTREME
        - risk_reasoning:       Why this risk level was assigned
        - confidence_reasoning: Why confidence is high/low
        - prediction_horizon:   Data-driven timeframe based on candle interval
        - actionable_insight:   Concrete next-step recommendation

Design Principles:
    1. No randomness — every sentence is derived from actual indicator values
    2. Modular — future LSTM predictions plug in without changing the interface
    3. Template-based NL — appropriate for rule-based signals (per Molnar, 2022)
    4. All fields are deterministic given the same input
    5. Prediction horizon is data-driven from candle_interval, not hardcoded
    6. detailed_reasoning uses sections (Technical Analysis / ML Forecast /
       Overall Recommendation) so ML content appears naturally when enabled

Usage:
    from ml.xdi.xdi_engine import XDIEngine

    xdi = XDIEngine()
    explanation = xdi.generate_explanation(signal_result)
"""

from datetime import datetime, timezone


# ---------------------------------------------------------------
# Candle-interval → prediction-horizon mapping
# ---------------------------------------------------------------
# Each entry: (display_label, timeframe_category, reasoning_template)
# The reasoning_template accepts {interval_label} and {display}.
HORIZON_MAP = {
    "1min": {
        "display": "next 5–15 minutes",
        "timeframe": "intraday",
        "reasoning": (
            "Using 1-minute candles, the signal is expected to play out "
            "within the next 5–15 minutes. This is a high-frequency "
            "horizon suited for scalping strategies."
        ),
    },
    "5min": {
        "display": "next 30–60 minutes",
        "timeframe": "intraday",
        "reasoning": (
            "Using 5-minute candles, the signal is expected to develop "
            "within the next 30–60 minutes. This horizon captures "
            "short-term intraday momentum shifts."
        ),
    },
    "15min": {
        "display": "next 1–4 hours",
        "timeframe": "intraday",
        "reasoning": (
            "Using 15-minute candles, the signal is projected over the "
            "next 1–4 hours. This horizon is suitable for day-trading "
            "strategies with moderate holding periods."
        ),
    },
    "1hour": {
        "display": "next trading day",
        "timeframe": "short-term",
        "reasoning": (
            "Using 1-hour candles, the signal targets the next full "
            "trading session. This horizon captures intraday trends "
            "and overnight gaps."
        ),
    },
    "1day": {
        "display": "next 5–10 trading days",
        "timeframe": "medium-term",
        "reasoning": (
            "Using daily candles, the signal is expected to develop over "
            "the next 5–10 trading days. This aligns with the natural "
            "periodicity of RSI(14), EMA(20), and Bollinger Band(20) "
            "indicators used in the analysis."
        ),
    },
}

# Fallback for unknown intervals (should not occur if pipeline validates)
_DEFAULT_HORIZON = {
    "display": "next 5–10 trading days",
    "timeframe": "medium-term",
    "reasoning": "Default horizon: re-evaluation in 5–10 trading days.",
}


class XDIEngine:
    """
    Explainable Decision Inference engine.

    Consumes a signal dictionary (as produced by SignalEngine.generate_signal,
    enriched by the pipeline with candle_interval and ml_prediction) and
    produces a structured explanation dictionary suitable for:
        - Display in the ProposalCard UI
        - Audit logging
        - API responses to the frontend
        - Future LLM-powered explanation enhancement

    The engine is stateless — each call is independent.
    """

    # --- Threshold constants matching SignalEngine ---
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_STRONG_OVERSOLD = 20
    RSI_STRONG_OVERBOUGHT = 80

    # Confidence tiers
    CONFIDENCE_HIGH = 0.70
    CONFIDENCE_MODERATE = 0.40

    def generate_explanation(self, signal_result: dict) -> dict:
        """
        Generate a complete natural-language explanation for a signal.

        Args:
            signal_result: Dictionary containing at minimum:
                signal, confidence, timestamp, indicators, rules_triggered.
                Optionally: candle_interval (str), ml_prediction (dict),
                rule_confidence (float), ml_confidence (float | None),
                hybrid_decision (dict from HybridDecisionEngine).

        Returns:
            Dictionary with keys:
                summary, detailed_reasoning, key_factors, risk_level,
                risk_reasoning, confidence_reasoning, prediction_horizon,
                actionable_insight, timestamp
        """
        signal          = signal_result["signal"]
        confidence      = signal_result["confidence"]
        indicators      = signal_result["indicators"]
        rules_triggered = signal_result["rules_triggered"]
        candle_interval = signal_result.get("candle_interval", "1day")
        ml_prediction   = signal_result.get("ml_prediction")
        rule_confidence = signal_result.get("rule_confidence", confidence)
        ml_confidence   = signal_result.get("ml_confidence")
        hybrid_decision = signal_result.get("hybrid_decision")

        # Extract hybrid context for grounded explanations
        agreement     = hybrid_decision.get("agreement", "NEUTRAL") if hybrid_decision else "NEUTRAL"
        final_signal  = (hybrid_decision.get("final_signal", signal)
                         if hybrid_decision else signal)

        # Build each explanation component
        summary = self._build_summary(
            final_signal, confidence, indicators, ml_prediction, agreement
        )
        key_factors = self._extract_key_factors(signal, indicators, rules_triggered)
        prediction_horizon = self._determine_prediction_horizon(candle_interval)
        risk_level, risk_reasoning = self._assess_risk(signal, confidence, indicators)
        confidence_reasoning = self._explain_confidence(
            signal, confidence, indicators, rule_confidence, ml_confidence,
        )
        actionable_insight = self._build_actionable_insight(
            final_signal, confidence, risk_level, indicators
        )
        detailed_reasoning = self._build_detailed_reasoning(
            signal, confidence, indicators, rules_triggered,
            key_factors, prediction_horizon, ml_prediction,
            rule_confidence, ml_confidence, agreement,
        )

        return {
            "summary":              summary,
            "detailed_reasoning":   detailed_reasoning,
            "key_factors":          key_factors,
            "risk_level":           risk_level,
            "risk_reasoning":       risk_reasoning,
            "confidence_reasoning": confidence_reasoning,
            "prediction_horizon":   prediction_horizon,
            "actionable_insight":   actionable_insight,
            "agreement":            agreement,
            "timestamp":            datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------
    def _build_summary(
        self,
        signal: str,
        confidence: float,
        indicators: dict,
        ml_prediction: dict | None = None,
        agreement: str = "NEUTRAL",
    ) -> str:
        """
        Build a one-sentence summary of the signal decision.

        When a hybrid decision is active, the summary reflects the agreement
        or conflict between technical and ML signals with actual values.
        """
        rsi   = indicators["rsi"]
        close = indicators["close"]
        confidence_label = self._confidence_label(confidence)

        ml_enabled  = bool(ml_prediction and ml_prediction.get("enabled"))
        change_pct  = ml_prediction.get("expected_change_percent") if ml_enabled else None
        pred_price  = ml_prediction.get("predicted_price") if ml_enabled else None
        horizon_lbl = (ml_prediction.get("prediction_horizon", "the forecast period")
                       if ml_enabled else "the forecast period")

        # ---- CONFLICT: technical and ML oppose each other ----
        if agreement == "CONFLICT" and ml_enabled and change_pct is not None:
            direction_word = "decline" if change_pct < 0 else "rise"
            return (
                f"HOLD is recommended despite {signal} technical indicators "
                f"because the LSTM forecasts a {change_pct:+.1f}% price "
                f"{direction_word} (to ${pred_price:.2f}) over {horizon_lbl}, "
                f"conflicting with the {signal} signal. "
                f"Conflicting evidence reduces position confidence."
            )

        # ---- STRONG or PARTIAL AGREEMENT with ML ----
        if agreement in ("STRONG_AGREEMENT", "PARTIAL_AGREEMENT") and ml_enabled and change_pct is not None:
            direction_word = "increase" if change_pct > 0 else "decrease"
            agr_word = "strongly" if agreement == "STRONG_AGREEMENT" else "partially"
            return (
                f"{signal} is recommended with {confidence_label} confidence ({confidence:.0%}). "
                f"RSI at {rsi:.1f} and technical indicators align with the signal, "
                f"and the LSTM also forecasts a {change_pct:+.1f}% price {direction_word} "
                f"(to ${pred_price:.2f}) — {agr_word} agreeing with the {signal} signal."
            )

        # ---- Default (no ML or neutral) ----
        if signal == "BUY":
            if rsi < self.RSI_STRONG_OVERSOLD:
                return (
                    f"Strong BUY signal detected with {confidence_label} confidence "
                    f"({confidence:.0%}). RSI at {rsi:.1f} indicates deeply oversold "
                    f"conditions at a price of {close:.2f}, suggesting a potential "
                    f"reversal opportunity."
                )
            return (
                f"BUY signal generated with {confidence_label} confidence "
                f"({confidence:.0%}). RSI at {rsi:.1f} is in oversold territory "
                f"at a price of {close:.2f}, with supporting momentum indicators "
                f"aligning for a bullish setup."
            )

        elif signal == "SELL":
            if rsi > self.RSI_STRONG_OVERBOUGHT:
                return (
                    f"Strong SELL signal detected with {confidence_label} confidence "
                    f"({confidence:.0%}). RSI at {rsi:.1f} indicates heavily overbought "
                    f"conditions at a price of {close:.2f}, suggesting a potential "
                    f"price correction."
                )
            return (
                f"SELL signal generated with {confidence_label} confidence "
                f"({confidence:.0%}). RSI at {rsi:.1f} is in overbought territory "
                f"at a price of {close:.2f}, with momentum indicators pointing "
                f"toward bearish pressure."
            )

        else:  # HOLD
            return (
                f"HOLD recommendation issued with {confidence_label} confidence "
                f"({confidence:.0%}). Technical indicators are showing mixed or "
                f"neutral signals at a price of {close:.2f} with RSI at {rsi:.1f}. "
                f"No clear directional bias detected."
            )


    # ------------------------------------------------------------------
    # Key factors extraction
    # ------------------------------------------------------------------
    def _extract_key_factors(
        self, signal: str, indicators: dict, rules_triggered: list[str]
    ) -> list[dict]:
        """
        Extract the most influential factors driving the signal.

        Each factor is a dict with:
            - indicator: name of the indicator
            - value: current value
            - interpretation: what this value means
            - impact: "bullish", "bearish", or "neutral"
        """
        rsi = indicators["rsi"]
        macd_hist = indicators["macd_histogram"]
        macd_line = indicators["macd_line"]
        macd_signal = indicators["macd_signal"]
        close = indicators["close"]
        ema_20 = indicators["ema_20"]
        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]

        factors = []

        # RSI factor
        if rsi < self.RSI_STRONG_OVERSOLD:
            rsi_interp = f"Deeply oversold at {rsi:.1f} — strong reversal potential"
            rsi_impact = "bullish"
        elif rsi < self.RSI_OVERSOLD:
            rsi_interp = f"Oversold at {rsi:.1f} — buying pressure likely increasing"
            rsi_impact = "bullish"
        elif rsi > self.RSI_STRONG_OVERBOUGHT:
            rsi_interp = f"Heavily overbought at {rsi:.1f} — strong correction potential"
            rsi_impact = "bearish"
        elif rsi > self.RSI_OVERBOUGHT:
            rsi_interp = f"Overbought at {rsi:.1f} — selling pressure likely increasing"
            rsi_impact = "bearish"
        elif 45 <= rsi <= 55:
            rsi_interp = f"Neutral at {rsi:.1f} — no directional bias"
            rsi_impact = "neutral"
        elif rsi < 45:
            rsi_interp = f"Leaning bearish at {rsi:.1f} — below midline"
            rsi_impact = "bearish"
        else:
            rsi_interp = f"Leaning bullish at {rsi:.1f} — above midline"
            rsi_impact = "bullish"

        factors.append({
            "indicator": "RSI (14)",
            "value": round(rsi, 2),
            "interpretation": rsi_interp,
            "impact": rsi_impact,
        })

        # MACD factor
        if macd_hist > 0 and macd_line > macd_signal:
            macd_interp = (
                f"Bullish — MACD line ({macd_line:.4f}) is above signal line "
                f"({macd_signal:.4f}) with positive histogram ({macd_hist:.4f})"
            )
            macd_impact = "bullish"
        elif macd_hist < 0 and macd_line < macd_signal:
            macd_interp = (
                f"Bearish — MACD line ({macd_line:.4f}) is below signal line "
                f"({macd_signal:.4f}) with negative histogram ({macd_hist:.4f})"
            )
            macd_impact = "bearish"
        else:
            macd_interp = (
                f"Converging — MACD histogram at {macd_hist:.4f}, "
                f"line and signal are close ({macd_line:.4f} vs {macd_signal:.4f})"
            )
            macd_impact = "neutral"

        factors.append({
            "indicator": "MACD (12, 26, 9)",
            "value": round(macd_hist, 4),
            "interpretation": macd_interp,
            "impact": macd_impact,
        })

        # Bollinger Bands factor
        bb_width = bb_upper - bb_lower
        price_position = (close - bb_lower) / bb_width if bb_width > 0 else 0.5

        if close < bb_lower:
            bb_interp = (
                f"Price ({close:.2f}) is below the lower band ({bb_lower:.2f}) — "
                f"statistically oversold, mean reversion expected"
            )
            bb_impact = "bullish"
        elif close > bb_upper:
            bb_interp = (
                f"Price ({close:.2f}) is above the upper band ({bb_upper:.2f}) — "
                f"statistically overbought, pullback expected"
            )
            bb_impact = "bearish"
        elif price_position < 0.3:
            bb_interp = (
                f"Price ({close:.2f}) is in the lower third of the bands "
                f"({bb_lower:.2f}–{bb_upper:.2f}) — leaning toward support"
            )
            bb_impact = "bullish"
        elif price_position > 0.7:
            bb_interp = (
                f"Price ({close:.2f}) is in the upper third of the bands "
                f"({bb_lower:.2f}–{bb_upper:.2f}) — approaching resistance"
            )
            bb_impact = "bearish"
        else:
            bb_interp = (
                f"Price ({close:.2f}) is near the middle band ({bb_middle:.2f}) — "
                f"within normal range ({bb_lower:.2f}–{bb_upper:.2f})"
            )
            bb_impact = "neutral"

        factors.append({
            "indicator": "Bollinger Bands (20, 2)",
            "value": round(price_position, 4),
            "interpretation": bb_interp,
            "impact": bb_impact,
        })

        # EMA trend factor
        ema_distance = close - ema_20
        ema_distance_pct = (ema_distance / ema_20) * 100 if ema_20 != 0 else 0

        if close > ema_20:
            ema_interp = (
                f"Price ({close:.2f}) is {abs(ema_distance_pct):.2f}% above "
                f"EMA-20 ({ema_20:.2f}) — short-term uptrend confirmed"
            )
            ema_impact = "bullish"
        elif close < ema_20:
            ema_interp = (
                f"Price ({close:.2f}) is {abs(ema_distance_pct):.2f}% below "
                f"EMA-20 ({ema_20:.2f}) — short-term downtrend confirmed"
            )
            ema_impact = "bearish"
        else:
            ema_interp = (
                f"Price ({close:.2f}) is at the EMA-20 ({ema_20:.2f}) — "
                f"trend is at an inflection point"
            )
            ema_impact = "neutral"

        factors.append({
            "indicator": "EMA (20)",
            "value": round(ema_20, 2),
            "interpretation": ema_interp,
            "impact": ema_impact,
        })

        return factors

    # ------------------------------------------------------------------
    # Detailed reasoning builder (sectioned: TA / ML / Overall)
    # ------------------------------------------------------------------
    def _build_detailed_reasoning(
        self,
        signal: str,
        confidence: float,
        indicators: dict,
        rules_triggered: list[str],
        key_factors: list[dict],
        prediction_horizon: dict,
        ml_prediction: dict | None,
        rule_confidence: float | None = None,
        ml_confidence: float | None = None,
        agreement: str = "NEUTRAL",
    ) -> str:
        """
        Build a sectioned analysis explaining the signal.

        Sections:
            1. Technical Analysis — indicator-by-indicator breakdown
            2. Machine Learning Forecast — only if ml_prediction.enabled
               (model-agnostic: uses prediction_type, not model name)
            3. Overall Recommendation — final verdict with confidence
               and hybrid agreement assessment when ML is active

        When ml_prediction is None or disabled, the ML section is
        simply omitted. The interface stays the same — no redesign
        needed when any ML model is integrated later.
        """
        sections = []

        # ---- Section 1: Technical Analysis ----
        ta_lines = ["Technical Analysis:"]

        # Bullet-point each key factor
        for factor in key_factors:
            ta_lines.append(f"• {factor['indicator']}: {factor['interpretation']}.")

        # Add rules triggered
        if rules_triggered:
            ta_lines.append("")
            ta_lines.append("Signal rules triggered:")
            for rule in rules_triggered:
                ta_lines.append(f"  → {rule}")

        sections.append("\n".join(ta_lines))

        # ---- Section 2: Machine Learning Forecast (conditional) ----
        if ml_prediction and ml_prediction.get("enabled"):
            ml_lines = ["Machine Learning Forecast:"]

            # Model-agnostic: use prediction_type for explanation,
            # mention model name only as metadata
            prediction_type = ml_prediction.get("prediction_type", "forecast")
            model_name      = ml_prediction.get("model")
            predicted_price = ml_prediction.get("predicted_price")
            change_pct      = ml_prediction.get("expected_change_percent")
            pred_confidence = ml_prediction.get("prediction_confidence")
            forecast_features = ml_prediction.get("forecast_features", [])
            horizon_display = prediction_horizon.get("display", "the forecast period")

            # Describe forecast type, not algorithm
            type_label = self._prediction_type_label(prediction_type)

            if predicted_price is not None:
                direction = "increase" if (change_pct and change_pct > 0) else "decrease"
                ml_lines.append(
                    f"• The {type_label} predicts the closing price may "
                    f"{direction} to ${predicted_price:.2f} within the "
                    f"{horizon_display}."
                )
            if change_pct is not None:
                direction = "upside" if change_pct > 0 else "downside"
                ml_lines.append(
                    f"• Expected {direction}: {'+' if change_pct > 0 else ''}{change_pct:.1f}%."
                )
            if pred_confidence is not None:
                conf_label = self._confidence_label(pred_confidence)
                ml_lines.append(
                    f"• Forecast confidence: {pred_confidence:.0%} ({conf_label})."
                )
            if forecast_features:
                ml_lines.append(
                    f"• Based on: {', '.join(forecast_features)}."
                )
            if model_name:
                ml_lines.append(f"• Model: {model_name}.")

            sections.append("\n".join(ml_lines))

        # ---- Section 3: Overall Recommendation ----
        overall_lines = ["Overall Recommendation:"]

        confidence_label = self._confidence_label(confidence)
        horizon_display  = prediction_horizon.get("display", "the projected period")

        if signal in ("BUY", "SELL"):
            overall_lines.append(
                f"{signal} with {confidence_label} confidence ({confidence:.0%}). "
                f"The signal is projected over the {horizon_display}."
            )

            # Factor count summary
            bullish_count = sum(1 for f in key_factors if f["impact"] == "bullish")
            bearish_count = sum(1 for f in key_factors if f["impact"] == "bearish")
            neutral_count = sum(1 for f in key_factors if f["impact"] == "neutral")
            overall_lines.append(
                f"Indicator alignment: {bullish_count} bullish, "
                f"{bearish_count} bearish, {neutral_count} neutral out of 4."
            )

            # Dual confidence note
            if ml_confidence is not None and rule_confidence is not None:
                overall_lines.append(
                    f"Confidence breakdown: rule engine {rule_confidence:.0%}, "
                    f"ML forecast {ml_confidence:.0%} → combined {confidence:.0%}."
                )
        else:
            overall_lines.append(
                f"HOLD — no clear directional bias detected. "
                f"Confidence in hold: {confidence:.0%} ({confidence_label}). "
                f"Re-evaluation suggested in the {horizon_display}."
            )

        # Hybrid agreement annotation (only when ML is active)
        if ml_prediction and ml_prediction.get("enabled") and agreement != "NEUTRAL":
            agreement_notes = {
                "STRONG_AGREEMENT":  "✓ Strong agreement between technical rules and ML forecast.",
                "PARTIAL_AGREEMENT": "⚠ Partial agreement — both sources aligned but confidence is moderate.",
                "CONFLICT":          "⚡ Conflict detected — technical and ML signals disagree. Signal downgraded to HOLD.",
            }
            note = agreement_notes.get(agreement)
            if note:
                overall_lines.append(note)

        sections.append("\n".join(overall_lines))

        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------
    def _assess_risk(
        self, signal: str, confidence: float, indicators: dict
    ) -> tuple[str, str]:
        """
        Assess the risk level of acting on this signal.

        Risk levels: LOW, MODERATE, HIGH, EXTREME

        Risk is derived from:
            - How far RSI is from extreme zones
            - Bollinger Band position (price outside bands = higher volatility risk)
            - Confidence level (lower confidence = higher risk)
            - Signal type (HOLD with low confidence = uncertain = higher risk)
        """
        rsi = indicators["rsi"]
        close = indicators["close"]
        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]

        risk_score = 0  # 0-10 scale
        risk_reasons = []

        # RSI extremity adds risk
        if rsi < self.RSI_STRONG_OVERSOLD or rsi > self.RSI_STRONG_OVERBOUGHT:
            risk_score += 3
            risk_reasons.append(
                f"RSI at {rsi:.1f} is at an extreme level, increasing the "
                f"probability of a sharp reversal"
            )
        elif rsi < self.RSI_OVERSOLD or rsi > self.RSI_OVERBOUGHT:
            risk_score += 2
            risk_reasons.append(
                f"RSI at {rsi:.1f} is in an extended zone, which carries "
                f"inherent reversal risk"
            )
        else:
            risk_reasons.append(
                f"RSI at {rsi:.1f} is within normal range, reducing momentum risk"
            )

        # Bollinger Band position
        if close < bb_lower or close > bb_upper:
            risk_score += 2
            risk_reasons.append(
                f"Price is outside the Bollinger Bands, indicating elevated "
                f"volatility and potential for mean reversion"
            )
        elif close < bb_middle - (bb_middle - bb_lower) * 0.7:
            risk_score += 1
            risk_reasons.append("Price is approaching the lower Bollinger Band")
        elif close > bb_middle + (bb_upper - bb_middle) * 0.7:
            risk_score += 1
            risk_reasons.append("Price is approaching the upper Bollinger Band")

        # Low confidence adds risk
        if confidence < self.CONFIDENCE_MODERATE:
            risk_score += 3
            risk_reasons.append(
                f"Signal confidence at {confidence:.0%} is low, indicating "
                f"weak indicator agreement"
            )
        elif confidence < self.CONFIDENCE_HIGH:
            risk_score += 1
            risk_reasons.append(
                f"Signal confidence at {confidence:.0%} is moderate"
            )

        # HOLD with conflicting signals
        if signal == "HOLD":
            risk_score += 1
            risk_reasons.append(
                "HOLD signal in an ambiguous market increases the risk "
                "of missed opportunities or adverse moves"
            )

        # Map score to level
        if risk_score <= 2:
            risk_level = "LOW"
        elif risk_score <= 4:
            risk_level = "MODERATE"
        elif risk_score <= 7:
            risk_level = "HIGH"
        else:
            risk_level = "EXTREME"

        risk_reasoning = (
            f"Risk assessment: {risk_level} (score {risk_score}/10). "
            + " ".join(risk_reasons)
            + "."
        )

        return risk_level, risk_reasoning

    # ------------------------------------------------------------------
    # Confidence explanation
    # ------------------------------------------------------------------
    def _explain_confidence(
        self,
        signal: str,
        confidence: float,
        indicators: dict,
        rule_confidence: float | None = None,
        ml_confidence: float | None = None,
    ) -> str:
        """
        Explain why confidence is at its current level.

        When both rule_confidence and ml_confidence are available,
        explains each source separately and how they combine.
        """
        rsi = indicators["rsi"]
        macd_hist = indicators["macd_histogram"]
        close = indicators["close"]
        ema_20 = indicators["ema_20"]
        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]

        base = ""
        if signal == "BUY":
            supporting = []
            if rsi < self.RSI_OVERSOLD:
                supporting.append(f"RSI ({rsi:.1f}) confirms oversold conditions")
            if macd_hist > 0:
                supporting.append(f"MACD histogram ({macd_hist:.4f}) shows bullish momentum")
            if close < bb_lower:
                supporting.append(f"price ({close:.2f}) below lower BB ({bb_lower:.2f})")
            if close > ema_20:
                supporting.append(f"price above EMA-20 ({ema_20:.2f}) confirms uptrend")
            elif close < ema_20:
                supporting.append(
                    f"however, price below EMA-20 ({ema_20:.2f}) weakens the bullish case"
                )

            if supporting:
                factors_text = "; ".join(supporting)
                base = (
                    f"Confidence is {confidence:.0%} ({self._confidence_label(confidence)}). "
                    f"Supporting factors: {factors_text}. "
                    f"{len(supporting)} out of 4 indicators align with the BUY signal."
                )

        elif signal == "SELL":
            supporting = []
            if rsi > self.RSI_OVERBOUGHT:
                supporting.append(f"RSI ({rsi:.1f}) confirms overbought conditions")
            if macd_hist < 0:
                supporting.append(f"MACD histogram ({macd_hist:.4f}) shows bearish momentum")
            if close > bb_upper:
                supporting.append(f"price ({close:.2f}) above upper BB ({bb_upper:.2f})")
            if close < ema_20:
                supporting.append(f"price below EMA-20 ({ema_20:.2f}) confirms downtrend")
            elif close > ema_20:
                supporting.append(
                    f"however, price above EMA-20 ({ema_20:.2f}) weakens the bearish case"
                )

            if supporting:
                factors_text = "; ".join(supporting)
                base = (
                    f"Confidence is {confidence:.0%} ({self._confidence_label(confidence)}). "
                    f"Supporting factors: {factors_text}. "
                    f"{len(supporting)} out of 4 indicators align with the SELL signal."
                )

        # HOLD or fallback if no supporting factors
        if not base:
            base = (
                f"Confidence is {confidence:.0%} ({self._confidence_label(confidence)}). "
                f"The indicators are not unanimously aligned — RSI is at {rsi:.1f} "
                f"(neutral zone), and the MACD histogram ({macd_hist:.4f}) is "
                f"{'slightly positive' if macd_hist > 0 else 'slightly negative' if macd_hist < 0 else 'flat'}. "
                f"More data points are needed before a directional bias can be established."
            )

        # Add dual confidence breakdown if ML is active
        if ml_confidence is not None and rule_confidence is not None:
            base += (
                f" The trading signal has {self._confidence_label(rule_confidence)} "
                f"rule confidence ({rule_confidence:.0%}), while the price forecast "
                f"has {self._confidence_label(ml_confidence)} confidence "
                f"({ml_confidence:.0%})."
            )

        return base

    # ------------------------------------------------------------------
    # Prediction horizon (data-driven from candle interval)
    # ------------------------------------------------------------------
    def _determine_prediction_horizon(self, candle_interval: str) -> dict:
        """
        Determine the prediction horizon from the candle interval.

        Instead of hardcoding timeframes, the horizon is derived from
        the data granularity. This makes the prediction horizon
        meaningful regardless of whether the pipeline runs on 1-minute
        or daily candles — and stays correct when LSTM is added later.

        Args:
            candle_interval: One of "1min", "5min", "15min", "1hour", "1day".

        Returns:
            Dictionary with keys:
                - display: human-readable horizon (e.g. "next 1–4 hours")
                - timeframe: category ("intraday", "short-term", "medium-term")
                - reasoning: why this horizon applies
                - candle_interval: the interval that drove this decision
        """
        horizon = HORIZON_MAP.get(candle_interval, _DEFAULT_HORIZON).copy()
        horizon["candle_interval"] = candle_interval
        return horizon

    # ------------------------------------------------------------------
    # Actionable insight
    # ------------------------------------------------------------------
    def _build_actionable_insight(
        self, signal: str, confidence: float, risk_level: str, indicators: dict
    ) -> str:
        """
        Build a concrete, actionable recommendation for the trader.
        """
        close = indicators["close"]
        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]
        ema_20 = indicators["ema_20"]

        if signal == "BUY":
            # Suggest stop-loss at recent support (lower BB) and target at middle/upper BB
            sl = round(bb_lower - (bb_middle - bb_lower) * 0.1, 2)
            tp = round(bb_middle + (bb_upper - bb_middle) * 0.5, 2)

            if risk_level in ("HIGH", "EXTREME"):
                return (
                    f"Consider a BUY entry near {close:.2f} with a tight "
                    f"stop-loss at {sl:.2f} (below lower Bollinger Band). "
                    f"Due to {risk_level} risk, use reduced position size "
                    f"(50-75% of normal). Target: {tp:.2f}. "
                    f"Risk-reward ratio: {abs(tp - close) / max(abs(close - sl), 0.01):.1f}:1."
                )
            return (
                f"Consider a BUY entry near {close:.2f} with stop-loss at "
                f"{sl:.2f} (below lower Bollinger Band) and initial target "
                f"at {tp:.2f} (mid-upper Bollinger range). "
                f"Risk-reward ratio: {abs(tp - close) / max(abs(close - sl), 0.01):.1f}:1."
            )

        elif signal == "SELL":
            # Suggest stop-loss above upper BB and target at middle/lower BB
            sl = round(bb_upper + (bb_upper - bb_middle) * 0.1, 2)
            tp = round(bb_middle - (bb_middle - bb_lower) * 0.5, 2)

            if risk_level in ("HIGH", "EXTREME"):
                return (
                    f"Consider a SELL/exit near {close:.2f} with a tight "
                    f"stop-loss at {sl:.2f} (above upper Bollinger Band). "
                    f"Due to {risk_level} risk, use reduced position size "
                    f"(50-75% of normal). Target: {tp:.2f}. "
                    f"Risk-reward ratio: {abs(close - tp) / max(abs(sl - close), 0.01):.1f}:1."
                )
            return (
                f"Consider a SELL/exit near {close:.2f} with stop-loss at "
                f"{sl:.2f} (above upper Bollinger Band) and initial target "
                f"at {tp:.2f} (mid-lower Bollinger range). "
                f"Risk-reward ratio: {abs(close - tp) / max(abs(sl - close), 0.01):.1f}:1."
            )

        else:  # HOLD
            return (
                f"No action recommended at the current price of {close:.2f}. "
                f"Monitor for RSI movement below {self.RSI_OVERSOLD} (buy signal) "
                f"or above {self.RSI_OVERBOUGHT} (sell signal). Key support level: "
                f"{bb_lower:.2f} (lower BB). Key resistance: {bb_upper:.2f} (upper BB). "
                f"EMA-20 trend pivot point: {ema_20:.2f}."
            )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    @staticmethod
    def _confidence_label(confidence: float) -> str:
        """Map a confidence float to a human-readable label."""
        if confidence >= 0.80:
            return "very high"
        elif confidence >= 0.65:
            return "high"
        elif confidence >= 0.45:
            return "moderate"
        elif confidence >= 0.25:
            return "low"
        else:
            return "very low"

    @staticmethod
    def _prediction_type_label(prediction_type: str) -> str:
        """
        Map a prediction_type to a human-readable description.

        Model-agnostic: describes *what* is being predicted,
        not *how* (algorithm name).
        """
        labels = {
            "price_forecast": "price forecast model",
            "direction": "directional prediction model",
            "volatility": "volatility forecast model",
            "regression": "regression model",
        }
        return labels.get(prediction_type, "ML model")
