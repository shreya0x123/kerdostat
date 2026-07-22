"""
app/routers/websocket.py
WebSocket endpoint that pushes live OHLCV tick updates to connected clients.
Fetches fresh data every 30 seconds and broadcasts to all connected clients.
"""
import asyncio
import json
import ssl
from datetime import datetime
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import yfinance as yf

ssl._create_default_https_context = ssl._create_unverified_context

router = APIRouter(tags=["WebSocket"])

# Store all active WebSocket connections
active_connections: List[WebSocket] = []


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


def fetch_latest_tick(symbol: str) -> dict:
    """Fetch the latest OHLCV tick for a symbol."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d")
    if df.empty:
        return {}
    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "date": str(df.index[-1])[:10],
        "open": round(float(latest["Open"]), 2),
        "high": round(float(latest["High"]), 2),
        "low": round(float(latest["Low"]), 2),
        "close": round(float(latest["Close"]), 2),
        "volume": int(latest["Volume"]),
        "timestamp": datetime.now().isoformat()
    }


@router.websocket("/ws/ohlcv/{symbol}")
async def websocket_ohlcv(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint: ws://localhost:8000/ws/ohlcv/{symbol}
    Connects client and pushes live OHLCV tick updates every 30 seconds.
    Client receives JSON with latest OHLCV data automatically.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Fetch latest tick
            tick = fetch_latest_tick(symbol.upper())
            if tick:
                await websocket.send_json({
                    "type": "tick",
                    "data": tick
                })
            # Wait 30 seconds before next push
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)