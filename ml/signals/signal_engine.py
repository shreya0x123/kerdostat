"""
Kerdostat Signal Engine
=======================
Rule-based signal generator that produces BUY / SELL / HOLD
recommendations from technical indicator values.

The engine uses clearly defined rules so that Day 3's XDI
(Explainable Decision Inference) engine can map each fired
rule to a natural-language justification.

Signal Rules:
    BUY  — RSI < 30 AND (MACD histogram > 0 OR Close < BB lower)
    SELL — RSI > 70 AND (MACD histogram < 0 OR Close > BB upper)
    HOLD — everything else

Confidence is computed from how many sub-conditions agree
(range: 0.0 to 1.0).

Usage:
    from ml.signals.signal_engine import SignalEngine

    engine = SignalEngine()
    result = engine.generate_signal(indicators_dict)
"""

from datetime import datetime, timezone


class SignalEngine:
    """
    Rule-based trading signal generator.

    Consumes a dictionary of technical indicator values (as produced
    by `compute_all_indicators`) and returns a structured signal dict.
    """

    # --- Threshold constants (easy to tune / expose via config) ---
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    def generate_signal(self, indicators: dict) -> dict:
        """
        Generate a BUY / SELL / HOLD signal from indicator values.

        Args:
            indicators: Dictionary with keys:
                rsi, ema_20, macd_line, macd_signal, macd_histogram,
                bb_upper, bb_middle, bb_lower, close

        Returns:
            Structured signal dictionary:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": float (0.0–1.0),
                "timestamp": ISO-8601 string,
                "indicators": { ... original indicator values ... },
                "rules_triggered": [ ... list of human-readable rule descriptions ... ]
            }
        """
        rsi = indicators["rsi"]
        macd_hist = indicators["macd_histogram"]
        close = indicators["close"]
        bb_upper = indicators["bb_upper"]
        bb_lower = indicators["bb_lower"]
        ema_20 = indicators["ema_20"]

        # ----------------------------------------------------------
        # Evaluate individual sub-conditions
        # ----------------------------------------------------------
        buy_conditions = []
        sell_conditions = []

        # RSI conditions
        if rsi < self.RSI_OVERSOLD:
            buy_conditions.append(
                f"RSI at {rsi:.1f} is below {self.RSI_OVERSOLD} (oversold territory)"
            )
        if rsi > self.RSI_OVERBOUGHT:
            sell_conditions.append(
                f"RSI at {rsi:.1f} is above {self.RSI_OVERBOUGHT} (overbought territory)"
            )

        # MACD histogram conditions
        if macd_hist > 0:
            buy_conditions.append(
                f"MACD histogram is positive ({macd_hist:.4f}), indicating bullish momentum"
            )
        if macd_hist < 0:
            sell_conditions.append(
                f"MACD histogram is negative ({macd_hist:.4f}), indicating bearish momentum"
            )

        # Bollinger Band conditions
        if close < bb_lower:
            buy_conditions.append(
                f"Price ({close:.2f}) is below the lower Bollinger Band ({bb_lower:.2f})"
            )
        if close > bb_upper:
            sell_conditions.append(
                f"Price ({close:.2f}) is above the upper Bollinger Band ({bb_upper:.2f})"
            )

        # EMA trend conditions (supplementary — affects confidence, not primary signal)
        if close > ema_20:
            buy_conditions.append(
                f"Price ({close:.2f}) is above EMA-20 ({ema_20:.2f}), confirming upward trend"
            )
        if close < ema_20:
            sell_conditions.append(
                f"Price ({close:.2f}) is below EMA-20 ({ema_20:.2f}), confirming downward trend"
            )

        # ----------------------------------------------------------
        # Determine signal using primary rules
        # ----------------------------------------------------------
        # Primary BUY rule:  RSI < 30 AND (MACD hist > 0 OR Close < BB lower)
        # Primary SELL rule: RSI > 70 AND (MACD hist < 0 OR Close > BB upper)
        rsi_oversold = rsi < self.RSI_OVERSOLD
        rsi_overbought = rsi > self.RSI_OVERBOUGHT
        macd_bullish = macd_hist > 0
        macd_bearish = macd_hist < 0
        below_bb = close < bb_lower
        above_bb = close > bb_upper

        is_buy = rsi_oversold and (macd_bullish or below_bb)
        is_sell = rsi_overbought and (macd_bearish or above_bb)

        if is_buy:
            signal = "BUY"
            rules_triggered = buy_conditions
        elif is_sell:
            signal = "SELL"
            rules_triggered = sell_conditions
        else:
            signal = "HOLD"
            rules_triggered = []

        # ----------------------------------------------------------
        # Compute confidence score (0.0 – 1.0)
        # ----------------------------------------------------------
        confidence = self._compute_confidence(
            signal=signal,
            rsi=rsi,
            macd_hist=macd_hist,
            close=close,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            ema_20=ema_20,
            buy_count=len(buy_conditions),
            sell_count=len(sell_conditions),
        )

        return {
            "signal": signal,
            "confidence": round(confidence, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": indicators,
            "rules_triggered": rules_triggered,
        }

    def _compute_confidence(
        self,
        signal: str,
        rsi: float,
        macd_hist: float,
        close: float,
        bb_upper: float,
        bb_lower: float,
        ema_20: float,
        buy_count: int,
        sell_count: int,
    ) -> float:
        """
        Compute a confidence score from 0.0 to 1.0 based on how many
        sub-conditions agree with the generated signal.

        For BUY/SELL: confidence scales with the number of supporting
        conditions (max 4 possible: RSI, MACD, BB, EMA).

        For HOLD: confidence reflects how neutral the indicators are —
        the closer RSI is to 50, the higher the confidence in holding.
        """
        max_conditions = 4  # RSI, MACD, BB, EMA

        if signal == "BUY":
            # Base confidence from condition count
            base = buy_count / max_conditions
            # Bonus for deeper oversold RSI
            rsi_depth = max(0, (self.RSI_OVERSOLD - rsi) / self.RSI_OVERSOLD)
            return min(1.0, base * 0.7 + rsi_depth * 0.3)

        elif signal == "SELL":
            # Base confidence from condition count
            base = sell_count / max_conditions
            # Bonus for deeper overbought RSI
            rsi_depth = max(0, (rsi - self.RSI_OVERBOUGHT) / (100 - self.RSI_OVERBOUGHT))
            return min(1.0, base * 0.7 + rsi_depth * 0.3)

        else:  # HOLD
            # Confidence in HOLD = how close RSI is to neutral (50)
            rsi_neutrality = 1.0 - abs(rsi - 50) / 50
            # Factor in mixed signals (neither side dominant)
            signal_balance = 1.0 - abs(buy_count - sell_count) / max(
                buy_count + sell_count, 1
            )
            return min(1.0, rsi_neutrality * 0.6 + signal_balance * 0.4)
