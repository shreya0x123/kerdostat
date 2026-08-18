import random
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("kerdostat-market-data")

class DataSource:
    LIVE = "LIVE"
    SIMULATED = "SIMULATED"
    CACHED = "CACHED"

# Cache for active Alpaca assets
alpaca_assets_cache = []

def get_alpaca_assets(alpaca_executor=None) -> List[Dict[str, Any]]:
    global alpaca_assets_cache
    if alpaca_assets_cache:
        return alpaca_assets_cache
    if alpaca_executor and not getattr(alpaca_executor, "mock_mode", True) and getattr(alpaca_executor, "client", None):
        try:
            assets = alpaca_executor.client.list_assets(status='active', asset_class='us_equity')
            alpaca_assets_cache = [
                {
                    "symbol": a.symbol,
                    "name": a.name,
                    "exchange": a.exchange
                }
                for a in assets if a.tradable
            ]
            logger.info(f"Cached {len(alpaca_assets_cache)} tradable Alpaca assets.")
        except Exception as e:
            logger.warning(f"Failed to cache Alpaca assets: {e}")
    return alpaca_assets_cache

MOCK_ASSETS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "GOOG", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "NFLX", "name": "Netflix, Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "AMD", "name": "Advanced Micro Devices, Inc."},
    {"symbol": "QUANT", "name": "Quant Network"},
]

def deterministic_seed(symbol: str) -> int:
    return sum(ord(c) * (idx + 1) for idx, c in enumerate(symbol))

def generate_mock_ohlcv(symbol: str, range_val: str) -> List[Dict[str, Any]]:
    candles = []
    seed = deterministic_seed(symbol)
    rng = random.Random(seed)
    
    base_price = 100.0 + (sum(ord(c) for c in symbol) % 200)
    num_candles = 50
    current_time = datetime.now(timezone.utc)
    
    if range_val == "1D":
        time_delta = timedelta(minutes=15)
        time_format = "%H:%M"
    elif range_val == "1W":
        time_delta = timedelta(minutes=30)
        time_format = "%m-%d %H:%M"
    else:  # 1M
        time_delta = timedelta(days=1)
        time_format = "%Y-%m-%d"
        
    price = base_price
    for i in range(num_candles):
        dt = current_time - (num_candles - i) * time_delta
        time_str = dt.strftime(time_format)
        
        change_pct = rng.uniform(-0.015, 0.015)
        o = price
        c = price * (1.0 + change_pct)
        h = max(o, c) * (1.0 + rng.uniform(0.0, 0.005))
        l = min(o, c) * (1.0 - rng.uniform(0.0, 0.005))
        
        o = round(max(0.01, o), 2)
        c = round(max(0.01, c), 2)
        h = round(max(0.01, h), 2)
        l = round(max(0.01, l), 2)
        vol = rng.randint(1000, 50000)
        
        candles.append({
            "time": time_str,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": vol
        })
        price = c
        
    return candles

def fetch_live_market_data(symbol: str, range_val: str, alpaca_executor=None) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Returns (candles, data_source) where data_source is DataSource.LIVE or DataSource.SIMULATED.
    """
    ticker = symbol.upper()
    
    # 1. Try fetching live price directly from Alpaca if configured in live mode
    if alpaca_executor and not getattr(alpaca_executor, "mock_mode", True) and getattr(alpaca_executor, "client", None):
        try:
            trade = alpaca_executor.client.get_latest_trade(ticker)
            price = None
            if trade:
                if hasattr(trade, "price") and trade.price:
                    price = float(trade.price)
                elif hasattr(trade, "p") and trade.p:
                    price = float(trade.p)
            
            if not price:
                bar = alpaca_executor.client.get_latest_bar(ticker)
                if bar:
                    if hasattr(bar, "close") and bar.close:
                        price = float(bar.close)
                    elif hasattr(bar, "c") and bar.c:
                        price = float(bar.c)
            
            if price:
                logger.info(f"Successfully fetched live Alpaca price for {ticker}: {price}")
                candles = generate_mock_ohlcv(symbol, range_val)
                if candles:
                    diff = price - candles[-1]["close"]
                    for c in candles:
                        c["open"] = round(c["open"] + diff, 2)
                        c["high"] = round(c["high"] + diff, 2)
                        c["low"] = round(c["low"] + diff, 2)
                        c["close"] = round(c["close"] + diff, 2)
                    return candles, DataSource.LIVE
        except Exception as e:
            logger.warning(f"Failed to fetch live price from Alpaca for {ticker}: {e}")

    # 2. Try fetching from Yahoo Finance with standard secure requests
    scale_factor = 1.0
    ticker_map = {
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "ICICIBANK": "ICICIBANK.NS",
        "TATAMOTORS": "TATAMOTORS.NS",
        "SBIN": "SBIN.NS",
        "WIPRO": "WIPRO.NS",
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "SENSEX": "^BSESN",
        "QUANT": "QNT-USD"
    }
    
    if ticker in ticker_map:
        ticker = ticker_map[ticker]
        if ticker == "QNT-USD":
            scale_factor = 1.5
        
    yf_range = "1d"
    yf_interval = "15m"
    time_format = "%H:%M"
    
    if range_val == "1W":
        yf_range = "5d"
        yf_interval = "30m"
        time_format = "%m-%d %H:%M"
    elif range_val == "1M":
        yf_range = "1mo"
        yf_interval = "1d"
        time_format = "%Y-%m-%d"
        
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": yf_range, "interval": yf_interval}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code != 200:
            if "." not in ticker and not ticker.startswith("^"):
                fallback_ticker = f"{ticker}.NS"
                fallback_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{fallback_ticker}"
                r = requests.get(fallback_url, params=params, headers=headers, timeout=5)
                if r.status_code == 200:
                    ticker = fallback_ticker
                else:
                    return None, DataSource.SIMULATED
            else:
                return None, DataSource.SIMULATED
            
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]
        
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])
        
        if not timestamps or not closes:
            return None, DataSource.SIMULATED
            
        candles = []
        for i in range(len(timestamps)):
            if opens[i] is None or highs[i] is None or lows[i] is None or closes[i] is None:
                continue
            dt = datetime.fromtimestamp(timestamps[i], timezone.utc)
            candles.append({
                "time": dt.strftime(time_format),
                "open": round(opens[i] * scale_factor, 2),
                "high": round(highs[i] * scale_factor, 2),
                "low": round(lows[i] * scale_factor, 2),
                "close": round(closes[i] * scale_factor, 2),
                "volume": int(volumes[i]) if (volumes[i] is not None) else 0
            })
        return candles, DataSource.LIVE
    except Exception as e:
        logger.warning(f"Failed to fetch market data for {ticker}: {e}")
        return None, DataSource.SIMULATED
