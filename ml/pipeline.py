"""
Kerdostat ML Pipeline Orchestrator
===================================
Single entry-point that ties together data loading, indicator
computation, signal generation, and explainable decision inference
into one function call.

Architecture:
    OHLCV Data
        │
        ├───────────────────┐
        ▼                   ▼
    Technical Rules     ML Model (future)
        │                   │
        └──────┬────────────┘
               ▼
      Recommendation Engine (combines TA + ML)
               ▼
         XDI Explanation

    The ML model predicts *prices*, NOT BUY/SELL/HOLD directly.
    The recommendation engine combines TA signals with ML forecasts
    to produce the final signal. This keeps the architecture modular
    and model-agnostic.

Pipeline steps:
    1. Load OHLCV data (CSV or Alpaca)
    2. Compute technical indicators
    3. Generate BUY / SELL / HOLD signal (rule-based)
    4. Attach ML prediction (placeholder / future model output)
    5. Compute combined confidence (rule + ML)
    6. Generate XDI explanation (natural-language justification)

Usage:
    from ml.pipeline import run_analysis

    # From CSV (daily candles — default)
    result = run_analysis(source="csv", filepath="data/sample_ohlcv.csv")

    # From Alpaca (15-minute candles)
    result = run_analysis(
        source="alpaca",
        symbol="AAPL",
        start="2025-01-01",
        end="2025-03-01",
        candle_interval="15min",
    )

    print(result["signal"])            # "BUY" / "SELL" / "HOLD"
    print(result["confidence"])        # 0.82  (combined)
    print(result["rule_confidence"])   # 0.86  (from TA rules)
    print(result["ml_confidence"])     # None  (until ML is enabled)
    print(result["ml_prediction"])     # { enabled, prediction_type, ... }
    print(result["explanation"])       # { summary, detailed_reasoning, ... }
"""

import json
from datetime import datetime, timezone

from data.loaders import load_alpaca, load_csv
from ml.indicators.technical_indicators import compute_all_indicators
from ml.signals.signal_engine import SignalEngine
from ml.xdi.xdi_engine import XDIEngine
from ml.decision.hybrid_decision_engine import HybridDecisionEngine


# Valid candle intervals and their human-readable labels
VALID_INTERVALS = {
    "1min":  "1 minute",
    "5min":  "5 minute",
    "15min": "15 minute",
    "1hour": "1 hour",
    "1day":  "1 day",
}


def _compute_combined_confidence(
    rule_confidence: float,
    ml_prediction: dict,
) -> float:
    """
    Compute the final combined confidence from rule engine and ML model.

    When ML is disabled:
        combined = rule_confidence  (100% weight to rules)

    When ML is enabled:
        combined = RULE_WEIGHT * rule_confidence
                 + ML_WEIGHT * prediction_confidence
        Weights can be tuned per model / strategy.
    """
    RULE_WEIGHT = 0.70
    ML_WEIGHT = 0.30

    if ml_prediction and ml_prediction.get("enabled"):
        ml_conf = ml_prediction.get("prediction_confidence")
        if ml_conf is not None:
            return round(
                RULE_WEIGHT * rule_confidence + ML_WEIGHT * ml_conf,
                4,
            )

    # ML not enabled or no confidence available — 100% rule confidence
    return rule_confidence


def _try_load_predictor(
    symbol: str | None,
    candle_interval: str,
    df,
):
    """
    Attempt to load a trained LSTMPredictor for the given symbol/interval.

    Returns the predictor if all artifacts exist and metadata is compatible.
    Returns None if any artifact is missing or incompatible — the pipeline
    then falls back to the disabled ml_prediction placeholder.

    This function never raises — failures are logged and silently bypassed.
    """
    if symbol is None:
        return None  # CSV source with no symbol can't resolve a model path

    try:
        from ml.data_pipeline.config import PipelineConfig    # lazy
        from ml.models.predictor import LSTMPredictor          # lazy

        cfg = PipelineConfig(
            symbol=symbol,
            candle_interval=candle_interval,
        )
        return LSTMPredictor.load_with_metadata(cfg)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug(
            "Could not load LSTM predictor: %s", exc
        )
        return None


def _disabled_ml_placeholder() -> dict:
    """Return the standard disabled ml_prediction schema."""
    return {
        "enabled":                  False,
        "prediction_type":          None,
        "model":                    None,
        "current_price":            None,
        "predicted_price":          None,
        "expected_change_percent":  None,
        "prediction_confidence":    None,
        "forecast_horizon_candles": None,
        "prediction_horizon":       None,
        "model_version":            None,
        "forecast_features":        [],
    }


def _candle_horizon_label(candle_interval: str) -> str:
    """Map candle interval to a human-readable prediction horizon string."""
    labels = {
        "1min":  "next 5–15 minutes",
        "5min":  "next 30–60 minutes",
        "15min": "next 1–4 hours",
        "1hour": "next trading day",
        "1day":  "next 5–10 trading days",
    }
    return labels.get(candle_interval, "next candle")


def run_analysis(
    source: str = "csv",
    filepath: str | None = None,
    symbol: str | None = None,
    start: str | None = None,
    end: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    candle_interval: str = "1day",
    **kwargs,
) -> dict:
    """
    Run the complete technical analysis pipeline.

    Steps:
        1. Load OHLCV data (CSV or Alpaca)
        2. Compute all technical indicators
        3. Generate a BUY / SELL / HOLD signal (rule-based)
        4. Attach ML prediction placeholder
        5. Compute combined confidence
        6. Generate XDI explanation (natural-language justification)

    Args:
        source: "csv" or "alpaca".
        filepath: Path to CSV file (required when source="csv").
        symbol: Ticker symbol (required when source="alpaca").
        start: Start date "YYYY-MM-DD" (required when source="alpaca").
        end: End date "YYYY-MM-DD" (required when source="alpaca").
        api_key: Alpaca API key (optional, can use env var).
        api_secret: Alpaca API secret (optional, can use env var).
        candle_interval: Candle/bar interval. One of:
            "1min", "5min", "15min", "1hour", "1day" (default).

    Returns:
        Structured signal dictionary:
        {
            "signal": "BUY" | "SELL" | "HOLD",
            "confidence": float,            # combined (rule + ML)
            "rule_confidence": float,       # from signal engine
            "ml_confidence": float | None,  # from ML model
            "timestamp": str,
            "indicators": dict,
            "rules_triggered": list[str],
            "candle_interval": str,
            "ml_prediction": dict,
            "explanation": dict,
            "source": str,
            "symbol": str | None
        }

    Raises:
        ValueError: If required arguments are missing for the chosen source,
                    or if candle_interval is invalid.
    """
    # Validate candle interval
    if candle_interval not in VALID_INTERVALS:
        raise ValueError(
            f"Invalid candle_interval '{candle_interval}'. "
            f"Must be one of: {list(VALID_INTERVALS.keys())}"
        )

    # -----------------------------------------------------------
    # Step 1: Load data
    # -----------------------------------------------------------
    if source == "csv":
        if not filepath:
            raise ValueError("filepath is required when source='csv'")
        df = load_csv(filepath)

    elif source == "alpaca":
        if not symbol or not start or not end:
            raise ValueError(
                "symbol, start, and end are required when source='alpaca'"
            )
        df = load_alpaca(
            symbol=symbol,
            start=start,
            end=end,
            api_key=api_key,
            api_secret=api_secret,
        )

    else:
        raise ValueError(
            f"Unknown source '{source}'. Use 'csv' or 'alpaca'."
        )

    # -----------------------------------------------------------
    # Step 2: Compute indicators
    # -----------------------------------------------------------
    indicators = compute_all_indicators(df)

    # -----------------------------------------------------------
    # Step 3: Generate signal (rule-based)
    # -----------------------------------------------------------
    engine = SignalEngine()
    result = engine.generate_signal(indicators)

    # -----------------------------------------------------------
    # Step 4: ML prediction (real LSTM or disabled placeholder)
    # -----------------------------------------------------------
    result["candle_interval"] = candle_interval
    generated_at = datetime.now(timezone.utc).isoformat()
    data_as_of   = str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(df.index[-1])

    predictor = _try_load_predictor(symbol, candle_interval, df)
    if predictor is not None:
        try:
            result["ml_prediction"] = predictor.predict(df, candle_interval)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "LSTM inference failed: %s — falling back to disabled.", exc
            )
            result["ml_prediction"] = _disabled_ml_placeholder()
    else:
        result["ml_prediction"] = _disabled_ml_placeholder()

    # -----------------------------------------------------------
    # Step 4b: Hybrid Decision (technical + ML combined)
    # -----------------------------------------------------------
    hybrid_engine = HybridDecisionEngine()
    result["hybrid_decision"] = hybrid_engine.combine(result, result["ml_prediction"])

    # Prediction validity fields (always present)
    result["generated_at"]       = generated_at
    result["data_as_of"]         = data_as_of
    result["prediction_horizon"] = result["ml_prediction"].get(
        "prediction_horizon",
        _candle_horizon_label(candle_interval),
    )

    # -----------------------------------------------------------
    # Step 5: Combined confidence
    # -----------------------------------------------------------
    # rule_confidence = signal engine confidence (always present)
    # ml_confidence   = ML model confidence (None when disabled)
    # confidence      = combined final confidence
    rule_confidence = result["confidence"]
    ml_confidence_val = (
        result["ml_prediction"].get("prediction_confidence")
        if result["ml_prediction"]["enabled"]
        else None
    )
    combined_confidence = _compute_combined_confidence(
        rule_confidence, result["ml_prediction"]
    )

    result["rule_confidence"] = rule_confidence
    result["ml_confidence"] = ml_confidence_val
    result["confidence"] = combined_confidence

    # -----------------------------------------------------------
    # Step 6: Generate XDI explanation
    # -----------------------------------------------------------
    xdi = XDIEngine()
    result["explanation"] = xdi.generate_explanation(result)

    # Add metadata about the data source
    result["source"] = source
    result["symbol"] = symbol

    return result


# -------------------------------------------------------------------
# CLI entry-point for quick testing
# -------------------------------------------------------------------
if __name__ == "__main__":
    import os

    # Default: run analysis on the sample CSV
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "sample_ohlcv.csv",
    )

    print("=" * 60)
    print("  Kerdostat Technical Analysis Pipeline")
    print("=" * 60)
    print()

    result = run_analysis(source="csv", filepath=csv_path)

    print(json.dumps(result, indent=2))
    print()
    print("─" * 60)
    print(f"  Signal:          {result['signal']}")
    print(f"  Confidence:      {result['confidence']}  (combined)")
    print(f"  Rule Confidence: {result['rule_confidence']}")
    print(f"  ML Confidence:   {result['ml_confidence']}")
    print(f"  Candle:          {result['candle_interval']}")
    print(f"  RSI:             {result['indicators']['rsi']}")
    print(f"  MACD Hist:       {result['indicators']['macd_histogram']}")
    print(f"  Close:           {result['indicators']['close']}")
    print()

    if result["rules_triggered"]:
        print("  Rules Triggered:")
        for rule in result["rules_triggered"]:
            print(f"    → {rule}")
    else:
        print("  No rules triggered (HOLD signal).")

    # ML Prediction
    ml = result.get("ml_prediction", {})
    print()
    print("─" * 60)
    print("  ML Prediction")
    print("─" * 60)
    if ml.get("enabled"):
        print(f"  Type:       {ml['prediction_type']}")
        print(f"  Model:      {ml['model']}")
        print(f"  Price:      {ml['predicted_price']}")
        print(f"  Change:     {ml['expected_change_percent']}%")
        print(f"  Confidence: {ml['prediction_confidence']}")
        if ml.get("forecast_features"):
            print(f"  Features:   {', '.join(ml['forecast_features'])}")
    else:
        print("  Status: Not enabled (placeholder for future ML integration)")

    # XDI Explanation output
    xdi = result.get("explanation", {})
    if xdi:
        print()
        print("─" * 60)
        print("  XDI Explanation")
        print("─" * 60)
        print(f"\n  Summary:\n    {xdi['summary']}")
        print(f"\n  Risk Level: {xdi['risk_level']}")
        horizon = xdi["prediction_horizon"]
        print(f"  Prediction Horizon: {horizon['display']} ({horizon['timeframe']})")
        print(f"\n  Key Factors:")
        for f in xdi["key_factors"]:
            icon = "▲" if f["impact"] == "bullish" else "▼" if f["impact"] == "bearish" else "●"
            print(f"    {icon} {f['indicator']}: {f['interpretation']}")
        print(f"\n  Actionable Insight:\n    {xdi['actionable_insight']}")

    print()
    print("=" * 60)
