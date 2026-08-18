import pytest
from app.core.signal_engine import calculate_signals

def test_insufficient_data():
    # Less than 30 candles
    data = [{"close": 100.0} for _ in range(20)]
    result = calculate_signals(data)
    assert result["signal"] == "HOLD"
    assert result["indicators"]["rsi"] is None
    assert result["indicators"]["close"] == 100.0

def test_signal_output_shape_and_keys():
    # 50 candles with random-walk close prices
    data = []
    base_price = 100.0
    for i in range(50):
        data.append({
            "open": base_price,
            "high": base_price + 2.0,
            "low": base_price - 2.0,
            "close": base_price + (i * 0.1), # slight upward trend
            "volume": 1000 + i
        })
    result = calculate_signals(data)
    
    # Check signal output keys
    assert "signal" in result
    assert "indicators" in result
    assert result["signal"] in ["BUY", "SELL", "HOLD"]
    
    indicators = result["indicators"]
    expected_keys = [
        "rsi", "macd_line", "macd_signal", "macd_histogram",
        "bbands_lower", "bbands_middle", "bbands_upper", "ema", "close"
    ]
    for key in expected_keys:
        assert key in indicators
        assert indicators[key] is not None
        assert isinstance(indicators[key], float)

def test_indicator_value_ranges():
    # Setup standard upward trend
    data = []
    for i in range(50):
        data.append({
            "open": 100.0 + i,
            "high": 102.0 + i,
            "low": 98.0 + i,
            "close": 101.0 + i,
            "volume": 1000
        })
    result = calculate_signals(data)
    indicators = result["indicators"]
    
    # RSI range check
    assert 0.0 <= indicators["rsi"] <= 100.0
    
    # Bollinger Bands check (lower <= middle <= upper)
    assert indicators["bbands_lower"] <= indicators["bbands_middle"]
    assert indicators["bbands_middle"] <= indicators["bbands_upper"]

def test_oversold_buy_trigger():
    # RSI under 30 and price below BBL
    # Create a steep drop to trigger oversold BUY signals
    data = []
    # 40 normal candles
    for i in range(40):
        data.append({
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000
        })
    # 10 collapsing candles
    for i in range(10):
        data.append({
            "open": 100.0 - (i * 5),
            "high": 100.0 - (i * 5) + 1.0,
            "low": 100.0 - (i * 5) - 6.0,
            "close": 100.0 - (i * 5) - 5.0,
            "volume": 1500
        })
        
    result = calculate_signals(data)
    # Check that score combines to return a BUY signal
    assert result["signal"] == "BUY"
    assert result["indicators"]["rsi"] < 30.0
    assert result["indicators"]["close"] < result["indicators"]["bbands_lower"]

def test_overbought_sell_trigger():
    # RSI above 70 and price above BBU
    # Create a steep rise to trigger overbought SELL signals
    data = []
    # 40 normal candles
    for i in range(40):
        data.append({
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000
        })
    # 10 skyrocketing candles
    for i in range(10):
        data.append({
            "open": 100.0 + (i * 5),
            "high": 100.0 + (i * 5) + 6.0,
            "low": 100.0 + (i * 5) - 1.0,
            "close": 100.0 + (i * 5) + 5.0,
            "volume": 1500
        })
        
    result = calculate_signals(data)
    # Check that score combines to return a SELL signal
    assert result["signal"] == "SELL"
    assert result["indicators"]["rsi"] > 70.0
    assert result["indicators"]["close"] > result["indicators"]["bbands_upper"]


def test_xai_reason_justification():
    # 1. Test HOLD with insufficient history
    data_short = [{"close": 100.0} for _ in range(10)]
    res_short = calculate_signals(data_short)
    assert "xai_reason" in res_short
    assert "justification" in res_short
    assert "XAIReason" in res_short
    assert isinstance(res_short["xai_reason"], str)
    assert len(res_short["xai_reason"]) > 0
    assert "insufficient history" in res_short["xai_reason"]

    # 2. Test normal HOLD
    data_hold = []
    for i in range(50):
        data_hold.append({
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000
        })
    res_hold = calculate_signals(data_hold)
    assert res_hold["signal"] == "HOLD"
    assert isinstance(res_hold["xai_reason"], str)
    assert len(res_hold["xai_reason"]) > 0
    assert "signal is HOLD because" in res_hold["xai_reason"]

    # 3. Test BUY (oversold)
    data_buy = []
    for i in range(40):
        data_buy.append({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000})
    for i in range(10):
        data_buy.append({"open": 100.0 - (i * 5), "high": 100.0 - (i * 5) + 1.0, "low": 100.0 - (i * 5) - 6.0, "close": 100.0 - (i * 5) - 5.0, "volume": 1500})
    res_buy = calculate_signals(data_buy)
    assert res_buy["signal"] == "BUY"
    assert isinstance(res_buy["xai_reason"], str)
    assert len(res_buy["xai_reason"]) > 0
    assert "signal is BUY because" in res_buy["xai_reason"]

    # 4. Test SELL (overbought)
    data_sell = []
    for i in range(40):
        data_sell.append({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000})
    for i in range(10):
        data_sell.append({"open": 100.0 + (i * 5), "high": 100.0 + (i * 5) + 6.0, "low": 100.0 + (i * 5) - 1.0, "close": 100.0 + (i * 5) + 5.0, "volume": 1500})
    res_sell = calculate_signals(data_sell)
    assert res_sell["signal"] == "SELL"
    assert isinstance(res_sell["xai_reason"], str)
    assert len(res_sell["xai_reason"]) > 0
    assert "signal is SELL because" in res_sell["xai_reason"]

def test_ml_model_predictions():
    from app.core.signal_engine import ml_model, predict_success_probability, calculate_signals
    
    # 1. Assert that the model is loaded
    assert ml_model is not None, "Model pkl should be successfully loaded on start"
    
    # 2. Test predict_success_probability with a valid indicator dict
    valid_indicators = {
        "rsi": 25.0,
        "macd_line": 1.2,
        "macd_signal": 0.8,
        "macd_histogram": 0.4,
        "bbands_lower": 95.0,
        "bbands_upper": 105.0,
        "ema": 100.0,
        "close": 94.0
    }
    prob = predict_success_probability(valid_indicators)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0
    
    # 3. Test that calculate_signals returns probability_success
    data = []
    # Create sufficient history
    for i in range(50):
        data.append({
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 101.0 - (i * 0.1),
            "volume": 1000
        })
    result = calculate_signals(data)
    assert "probability_success" in result
    assert isinstance(result["probability_success"], float)
    assert 0.0 <= result["probability_success"] <= 1.0
    
    # 4. Test that xai_reason contains predicted signal success probability percentage
    assert "predicted signal success probability of" in result["xai_reason"]

