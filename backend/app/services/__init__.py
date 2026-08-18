from app.core.alpaca_executor import AlpacaExecutor
from app.core.fyers_executor import FyersExecutor
from app.core.guardrails import GuardrailEngine
from app.services.market_data import fetch_live_market_data, generate_mock_ohlcv, get_alpaca_assets, MOCK_ASSETS

# Shared singleton broker instances
alpaca_executor = AlpacaExecutor()
fyers_executor = FyersExecutor()
guardrail_engine = GuardrailEngine()

def select_executor_by_symbol(symbol: str):
    sym = symbol.upper()
    if sym.endswith(".NS") or sym.endswith(".BO") or sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS", "SBIN", "WIPRO", "NIFTY", "SENSEX"]:
        return fyers_executor
    return alpaca_executor

__all__ = [
    "alpaca_executor",
    "fyers_executor",
    "guardrail_engine",
    "select_executor_by_symbol",
    "fetch_live_market_data",
    "generate_mock_ohlcv",
    "get_alpaca_assets",
    "MOCK_ASSETS"
]
