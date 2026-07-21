import os
import logging
import pandas as pd
import pandas_ta as ta
import joblib
import numpy as np

logger = logging.getLogger("kerdostat-signal-engine")

# Load XAI ML model
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")
ml_model = None
if os.path.exists(MODEL_PATH):
    try:
        ml_model = joblib.load(MODEL_PATH)
        logger.info(f"Loaded XAI ML model from {MODEL_PATH}")
    except Exception as e:
        logger.warning(f"Failed to load XAI ML model: {e}")
else:
    logger.warning(f"XAI ML model file not found at {MODEL_PATH}")

def predict_success_probability(indicators: dict) -> float:
    # Default return value when model is not available or indicators are missing
    if ml_model is None:
        return 0.50
        
    rsi_val = indicators.get("rsi")
    macd_line = indicators.get("macd_line")
    macd_sig = indicators.get("macd_signal")
    macd_hist = indicators.get("macd_histogram")
    bb_lower = indicators.get("bbands_lower")
    bb_upper = indicators.get("bbands_upper")
    ema_val = indicators.get("ema")
    close_val = indicators.get("close")
    
    # If any essential indicator is None, return a fallback probability
    if any(v is None for v in [rsi_val, macd_line, macd_sig, macd_hist, bb_lower, bb_upper, ema_val, close_val]):
        return 0.50
        
    try:
        # Construct the scale-invariant features matching train_xai.py:
        # 1. rsi
        # 2. macd_line
        # 3. macd_sig
        # 4. macd_hist
        # 5. close_minus_ema (percentage deviation: (close_val - ema_val) / ema_val * 100.0)
        # 6. bb_percent (relative position: (close_val - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5)
        
        close_minus_ema = ((close_val - ema_val) / ema_val) * 100.0 if ema_val != 0 else 0.0
        bb_denom = bb_upper - bb_lower
        bb_percent = (close_val - bb_lower) / bb_denom if bb_denom > 0 else 0.5
        bb_percent = max(0.0, min(1.0, bb_percent))
        
        features = np.array([[rsi_val, macd_line, macd_sig, macd_hist, close_minus_ema, bb_percent]])
        proba = ml_model.predict_proba(features)
        return float(proba[0][1])
    except Exception as e:
        logger.error(f"Error predicting success probability: {e}")
        return 0.50

def generate_justification(signal: str, indicators: dict, success_probability: float) -> str:
    rsi_val = indicators.get("rsi")
    macd_line = indicators.get("macd_line")
    macd_sig = indicators.get("macd_signal")
    macd_hist = indicators.get("macd_histogram")
    bb_lower = indicators.get("bbands_lower")
    bb_upper = indicators.get("bbands_upper")
    ema_val = indicators.get("ema")
    close_val = indicators.get("close")
    
    rsi_str = f"{rsi_val:.2f}" if rsi_val is not None else "N/A"
    macd_sig_str = f"{macd_sig:.2f}" if macd_sig is not None else "N/A"
    
    prefix = f"RSI at {rsi_str}, MACD crossed {macd_sig_str}, signal is {signal} because"
    prob_pct = success_probability * 100.0
    
    if rsi_val is None or close_val is None:
        explanation = "insufficient history is available to compute technical indicators"
        return f"{prefix} {explanation} with a predicted signal success probability of {prob_pct:.1f}%."
        
    is_oversold = (rsi_val < 30) and (bb_lower is not None and close_val < bb_lower)
    is_overbought = (rsi_val > 70) and (bb_upper is not None and close_val > bb_upper)
    is_bullish_trend = (ema_val is not None and close_val > ema_val) and (macd_hist is not None and macd_hist > 0)
    is_bearish_trend = (ema_val is not None and close_val < ema_val) and (macd_hist is not None and macd_hist < 0)
    
    explanation = ""
    if signal == "BUY":
        if is_oversold:
            explanation = f"RSI is under 30 (oversold) and the closing price ({close_val:.2f}) is below the lower Bollinger Band ({bb_lower:.2f})"
        else:
            ema_str = f"{ema_val:.2f}" if ema_val is not None else "N/A"
            macd_hist_str = f"{macd_hist:.2f}" if macd_hist is not None else "N/A"
            explanation = f"the closing price ({close_val:.2f}) is above the 20-period EMA ({ema_str}) and the MACD histogram ({macd_hist_str}) shows bullish momentum"
    elif signal == "SELL":
        if is_overbought:
            explanation = f"RSI is over 70 (overbought) and the closing price ({close_val:.2f}) is above the upper Bollinger Band ({bb_upper:.2f})"
        else:
            ema_str = f"{ema_val:.2f}" if ema_val is not None else "N/A"
            macd_hist_str = f"{macd_hist:.2f}" if macd_hist is not None else "N/A"
            explanation = f"the closing price ({close_val:.2f}) is below the 20-period EMA ({ema_str}) and the MACD histogram ({macd_hist_str}) shows bearish momentum"
    else: # HOLD
        if is_bullish_trend and rsi_val > 70:
            explanation = "the asset is in a bullish trend but RSI is above 70 (overbought), indicating short-term pullback risk"
        elif is_bearish_trend and rsi_val < 30:
            explanation = "the asset is in a bearish trend but RSI is below 30 (oversold), indicating potential consolidation"
        else:
            explanation = "there is no strong confluence of mean-reversion or trend-following signals"
            
    return f"{prefix} {explanation} with a predicted signal success probability of {prob_pct:.1f}%."

def calculate_confidence(signal: str, indicators: dict) -> float:
    if signal == "HOLD":
        return 0.50
        
    rsi_val = indicators.get("rsi")
    macd_hist = indicators.get("macd_histogram")
    bb_lower = indicators.get("bbands_lower")
    bb_upper = indicators.get("bbands_upper")
    ema_val = indicators.get("ema")
    close_val = indicators.get("close")
    
    score = 0.0
    if signal == "BUY":
        if rsi_val is not None and rsi_val < 30:
            score += 0.3
        elif rsi_val is not None and rsi_val < 50:
            score += 0.1
            
        if close_val is not None and bb_lower is not None and close_val < bb_lower:
            score += 0.3
            
        if close_val is not None and ema_val is not None and close_val > ema_val:
            score += 0.2
            
        if macd_hist is not None and macd_hist > 0:
            score += 0.2
            
    elif signal == "SELL":
        if rsi_val is not None and rsi_val > 70:
            score += 0.3
        elif rsi_val is not None and rsi_val > 50:
            score += 0.1
            
        if close_val is not None and bb_upper is not None and close_val > bb_upper:
            score += 0.3
            
        if close_val is not None and ema_val is not None and close_val < ema_val:
            score += 0.2
            
        if macd_hist is not None and macd_hist < 0:
            score += 0.2
            
    return round(max(0.1, min(1.0, score)), 2)

def calculate_signals(ohlcv_data: list) -> dict:
    """
    Computes technical indicators (RSI, MACD, Bollinger Bands, EMA) using pandas-ta
    and combines them to return a signal (BUY/SELL/HOLD) and the latest indicator values.
    
    ohlcv_data should be a list of dictionaries, e.g.:
    [
        {"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000, "time": "10:00"},
        ...
    ]
    """
    # 1. Fallback / Validation
    if not ohlcv_data or len(ohlcv_data) < 30:
        logger.warning(f"Insufficient history ({len(ohlcv_data) if ohlcv_data else 0} rows). Min 30 required.")
        indicators_dict = {
            "rsi": None,
            "macd_line": None,
            "macd_signal": None,
            "macd_histogram": None,
            "bbands_lower": None,
            "bbands_middle": None,
            "bbands_upper": None,
            "ema": None,
            "close": ohlcv_data[-1]["close"] if ohlcv_data else None
        }
        xai_reason = generate_justification("HOLD", indicators_dict, 0.50)
        return {
            "signal": "HOLD",
            "indicators": indicators_dict,
            "xai_reason": xai_reason,
            "justification": xai_reason,
            "XAIReason": xai_reason,
            "confidence_score": 0.50,
            "probability_success": 0.50
        }

    try:
        # Convert list of dicts to pandas DataFrame
        df = pd.DataFrame(ohlcv_data)
        
        # Ensure correct datatypes
        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["open"] = pd.to_numeric(df["open"])
        df["volume"] = pd.to_numeric(df["volume"])

        # 2. Compute indicators using pandas_ta
        # RSI 14-period
        rsi_series = df.ta.rsi(length=14)
        
        # MACD (12, 26, 9)
        macd_df = df.ta.macd(fast=12, slow=26, signal=9)
        
        # Bollinger Bands (20-period, 2 std)
        bbands_df = df.ta.bbands(length=20, std=2)
        
        # EMA (20-period)
        ema_series = df.ta.ema(length=20)

        # 3. Pull latest values (last row)
        latest_idx = df.index[-1]
        
        # Extract closing price
        close_val = float(df.loc[latest_idx, "close"])
        
        # Extract RSI
        rsi_val = rsi_series.loc[latest_idx] if rsi_series is not None else None
        rsi_val = float(rsi_val) if pd.notna(rsi_val) else None
        
        # Extract MACD
        macd_line = None
        macd_sig = None
        macd_hist = None
        if macd_df is not None:
            col_line = next((col for col in macd_df.columns if "MACD_" in col), None)
            col_sig = next((col for col in macd_df.columns if "MACDs_" in col), None)
            col_hist = next((col for col in macd_df.columns if "MACDh_" in col), None)
            
            if col_line: macd_line = float(macd_df.loc[latest_idx, col_line]) if pd.notna(macd_df.loc[latest_idx, col_line]) else None
            if col_sig: macd_sig = float(macd_df.loc[latest_idx, col_sig]) if pd.notna(macd_df.loc[latest_idx, col_sig]) else None
            if col_hist: macd_hist = float(macd_df.loc[latest_idx, col_hist]) if pd.notna(macd_df.loc[latest_idx, col_hist]) else None

        # Extract Bollinger Bands
        bb_lower = None
        bb_middle = None
        bb_upper = None
        if bbands_df is not None:
            col_lower = next((col for col in bbands_df.columns if "BBL_" in col), None)
            col_middle = next((col for col in bbands_df.columns if "BBM_" in col), None)
            col_upper = next((col for col in bbands_df.columns if "BBU_" in col), None)
            
            if col_lower: bb_lower = float(bbands_df.loc[latest_idx, col_lower]) if pd.notna(bbands_df.loc[latest_idx, col_lower]) else None
            if col_middle: bb_middle = float(bbands_df.loc[latest_idx, col_middle]) if pd.notna(bbands_df.loc[latest_idx, col_middle]) else None
            if col_upper: bb_upper = float(bbands_df.loc[latest_idx, col_upper]) if pd.notna(bbands_df.loc[latest_idx, col_upper]) else None

        # Extract EMA
        ema_val = ema_series.loc[latest_idx] if ema_series is not None else None
        ema_val = float(ema_val) if pd.notna(ema_val) else None

        # 4. Multi-Indicator Confluence Scoring Logic
        # A. Mean Reversion Triggers
        is_oversold = (rsi_val is not None and rsi_val < 30) and (bb_lower is not None and close_val < bb_lower)
        is_overbought = (rsi_val is not None and rsi_val > 70) and (bb_upper is not None and close_val > bb_upper)
        
        # B. Trend Following Triggers
        is_bullish_trend = (ema_val is not None and close_val > ema_val) and (macd_hist is not None and macd_hist > 0)
        is_bearish_trend = (ema_val is not None and close_val < ema_val) and (macd_hist is not None and macd_hist < 0)

        # C. Combined Decision Mapping
        if is_oversold:
            signal = "BUY"
        elif is_overbought:
            signal = "SELL"
        elif is_bullish_trend:
            # Prevent buying trend if RSI is already in overbought territory
            if rsi_val is not None and rsi_val > 70:
                signal = "HOLD"
            else:
                signal = "BUY"
        elif is_bearish_trend:
            # Prevent selling trend if RSI is already in oversold territory
            if rsi_val is not None and rsi_val < 30:
                signal = "HOLD"
            else:
                signal = "SELL"
        else:
            signal = "HOLD"

        indicators_dict = {
            "rsi": rsi_val,
            "macd_line": macd_line,
            "macd_signal": macd_sig,
            "macd_histogram": macd_hist,
            "bbands_lower": bb_lower,
            "bbands_middle": bb_middle,
            "bbands_upper": bb_upper,
            "ema": ema_val,
            "close": close_val
        }
        
        prob_val = predict_success_probability(indicators_dict)
        xai_reason = generate_justification(signal, indicators_dict, prob_val)
        confidence_score = calculate_confidence(signal, indicators_dict)

        return {
            "signal": signal,
            "indicators": indicators_dict,
            "xai_reason": xai_reason,
            "justification": xai_reason,
            "XAIReason": xai_reason,
            "confidence_score": confidence_score,
            "probability_success": prob_val
        }

    except Exception as e:
        logger.error(f"Error computing signals: {e}")
        indicators_dict = {
            "rsi": None,
            "macd_line": None,
            "macd_signal": None,
            "macd_histogram": None,
            "bbands_lower": None,
            "bbands_middle": None,
            "bbands_upper": None,
            "ema": None,
            "close": ohlcv_data[-1]["close"] if (ohlcv_data and "close" in ohlcv_data[-1]) else None
        }
        xai_reason = generate_justification("HOLD", indicators_dict, 0.50)
        return {
            "signal": "HOLD",
            "indicators": indicators_dict,
            "xai_reason": xai_reason,
            "justification": xai_reason,
            "XAIReason": xai_reason,
            "confidence_score": 0.50,
            "probability_success": 0.50
        }
