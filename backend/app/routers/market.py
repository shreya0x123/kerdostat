import logging
import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Any
from fastapi import APIRouter, Query

from app.services import (
    fetch_live_market_data,
    generate_mock_ohlcv,
    get_alpaca_assets,
    MOCK_ASSETS,
    alpaca_executor
)
from app.core.signal_engine import calculate_signals

logger = logging.getLogger("kerdostat-market-router")
router = APIRouter(tags=["Market Data & Signals"])

@router.get("/market/search")
def search_assets(q: str = ""):
    q = q.upper().strip()
    if not q:
        return []
    
    assets = get_alpaca_assets(alpaca_executor)
    if not assets:
        assets = MOCK_ASSETS
        
    results = []
    for a in assets:
        if a["symbol"].startswith(q) or q in a["name"].upper():
            results.append({
                "symbol": a["symbol"],
                "name": a["name"]
            })
            if len(results) >= 8:
                break
                
    symbols = [r["symbol"] for r in results]
    prices_dict = {}
    
    if symbols and alpaca_executor and not getattr(alpaca_executor, "mock_mode", True) and getattr(alpaca_executor, "client", None):
        try:
            trades = alpaca_executor.client.get_latest_trades(symbols)
            for sym, t in trades.items():
                p = float(t.price) if hasattr(t, "price") else float(t.p) if hasattr(t, "p") else None
                if p:
                    prices_dict[sym] = {
                        "price": p,
                        "change": round(p * 0.003, 2),
                        "change_percent": 0.35
                    }
        except Exception as e:
            logger.warning(f"Failed to batch fetch trades in search: {e}")
            
    for r in results:
        sym = r["symbol"]
        if sym not in prices_dict:
            base_price = 100.0 + (sum(ord(c) for c in sym) % 200)
            change_val = round(base_price * 0.008, 2)
            change_pct = 0.8
            if len(sym) % 2 == 0:
                change_val = -change_val
                change_pct = -change_pct
            prices_dict[sym] = {
                "price": base_price,
                "change": change_val,
                "change_percent": change_pct
            }
        r["price"] = prices_dict[sym]["price"]
        r["change"] = prices_dict[sym]["change"]
        r["change_percent"] = prices_dict[sym]["change_percent"]
        
    return results

@router.get("/market/ohlcv", response_model=List[Dict[str, Any]])
def get_market_ohlcv(symbol: str = "QUANT", range_val: str = Query("1D", alias="range")):
    live_candles = fetch_live_market_data(symbol, range_val, alpaca_executor)
    if not live_candles or len(live_candles) < 30:
        live_candles = generate_mock_ohlcv(symbol, range_val)
        
    df = pd.DataFrame(live_candles)
    df["close"] = pd.to_numeric(df["close"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["open"] = pd.to_numeric(df["open"])
    df["volume"] = pd.to_numeric(df["volume"])
    
    rsi_series = df.ta.rsi(length=14)
    df["rsi"] = rsi_series if rsi_series is not None else None
    
    ema_series = df.ta.ema(length=20)
    df["ema"] = ema_series if ema_series is not None else None
    
    bb = df.ta.bbands(length=20, std=2)
    if bb is not None:
        col_lower = next((col for col in bb.columns if "BBL_" in col), None)
        col_middle = next((col for col in bb.columns if "BBM_" in col), None)
        col_upper = next((col for col in bb.columns if "BBU_" in col), None)
        if col_lower: df["bbands_lower"] = bb[col_lower]
        if col_middle: df["bbands_middle"] = bb[col_middle]
        if col_upper: df["bbands_upper"] = bb[col_upper]
        
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None:
        col_line = next((col for col in macd.columns if "MACD_" in col), None)
        col_sig = next((col for col in macd.columns if "MACDs_" in col), None)
        col_hist = next((col for col in macd.columns if "MACDh_" in col), None)
        if col_line: df["macd_line"] = macd[col_line]
        if col_sig: df["macd_signal"] = macd[col_sig]
        if col_hist: df["macd_histogram"] = macd[col_hist]

    for i in range(len(live_candles)):
        c = live_candles[i]
        c["rsi"] = round(float(df.loc[i, "rsi"]), 2) if "rsi" in df.columns and pd.notna(df.loc[i, "rsi"]) else None
        c["ema"] = round(float(df.loc[i, "ema"]), 2) if "ema" in df.columns and pd.notna(df.loc[i, "ema"]) else None
        c["bbands_lower"] = round(float(df.loc[i, "bbands_lower"]), 2) if "bbands_lower" in df.columns and pd.notna(df.loc[i, "bbands_lower"]) else None
        c["bbands_middle"] = round(float(df.loc[i, "bbands_middle"]), 2) if "bbands_middle" in df.columns and pd.notna(df.loc[i, "bbands_middle"]) else None
        c["bbands_upper"] = round(float(df.loc[i, "bbands_upper"]), 2) if "bbands_upper" in df.columns and pd.notna(df.loc[i, "bbands_upper"]) else None
        c["macd_line"] = round(float(df.loc[i, "macd_line"]), 2) if "macd_line" in df.columns and pd.notna(df.loc[i, "macd_line"]) else None
        c["macd_signal"] = round(float(df.loc[i, "macd_signal"]), 2) if "macd_signal" in df.columns and pd.notna(df.loc[i, "macd_signal"]) else None
        c["macd_histogram"] = round(float(df.loc[i, "macd_histogram"]), 2) if "macd_histogram" in df.columns and pd.notna(df.loc[i, "macd_histogram"]) else None
        
    return live_candles[-30:]

@router.get("/market/signal")
def get_market_signal(symbol: str = "QUANT", range_val: str = Query("1D", alias="range")):
    live_candles = fetch_live_market_data(symbol, range_val, alpaca_executor)
    if not live_candles or len(live_candles) < 30:
        live_candles = generate_mock_ohlcv(symbol, range_val)
    return calculate_signals(live_candles)
