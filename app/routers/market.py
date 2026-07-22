from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import redis
import yfinance as yf
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/market", tags=["Market"])

try:
    redis_client = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("Redis connected successfully")
except Exception:
    redis_client = None
    print("Redis not available - caching disabled")

CACHE_TTL = 60

class OHLCVResponse(BaseModel):
    symbol: str
    data: list
    cached: bool
    cache_ttl: Optional[int] = None

@router.get("/ohlcv/{symbol}", response_model=OHLCVResponse, summary="Get live OHLCV market data with Redis caching")
def get_ohlcv(
    symbol: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cache_key = f"ohlcv:{symbol}:{limit}"
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return OHLCVResponse(
                    symbol=symbol,
                    data=json.loads(cached_data),
                    cached=True,
                    cache_ttl=redis_client.ttl(cache_key)
                )
        except Exception:
            pass
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1mo")
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        df = df.tail(limit)
        records = []
        for idx, row in df.iterrows():
            records.append({
                "date": str(idx)[:10],
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        if redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL, json.dumps(records))
            except Exception:
                pass
        return OHLCVResponse(symbol=symbol, data=records, cached=False)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market data error: {str(e)}")
