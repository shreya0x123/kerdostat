import logging
import random
import os
import json
import asyncio
import sys
import redis.asyncio as aioredis
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Cookie, Depends, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import urllib3
import requests

# Load local .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip("'\"")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kerdostat-backend")

app = FastAPI(title="Kerdostat Live Trading API", version="1.0.0")

from app.core.alpaca_executor import AlpacaExecutor
from app.core.fyers_executor import FyersExecutor
from app.core.guardrails import GuardrailEngine

alpaca_executor = AlpacaExecutor()
fyers_executor = FyersExecutor()
guardrail_engine = GuardrailEngine()

def select_executor_by_symbol(symbol: str):
    sym = symbol.upper()
    if sym.endswith(".NS") or sym.endswith(".BO") or sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS", "SBIN", "WIPRO", "NIFTY", "SENSEX"]:
        return fyers_executor
    return alpaca_executor

# Database configuration
DATABASE_URL = "sqlite:///./kerdostat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

class ProposalModel(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    signal = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    SL = Column(Float, nullable=False)
    TP = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending")
    XAIReason = Column(String, nullable=True)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    timestamp = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    user = Column(String, nullable=False)

class SystemStateModel(Base):
    __tablename__ = "system_state"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

# Seed function
def seed_db(db: Session):
    if db.query(UserModel).count() == 0:
        db.add(UserModel(
            id="user-1",
            name="Alex Mercer",
            email="trader@kerdostat.com",
            password="password123"
        ))
    if db.query(ProposalModel).count() == 0:
        db.add(ProposalModel(
            id="prop-1",
            symbol="QUANT",
            signal="BUY",
            qty=150,
            SL=149.0,
            TP=157.5,
            status="pending",
            XAIReason="Neural network identified a triple-bottom support pattern at $149.50 with a confirmed breakout above the 50-period SMA on the 15-minute timeframe. Relative strength index (RSI) turned upward from oversold boundaries."
        ))
        db.add(ProposalModel(
            id="prop-2",
            symbol="NVDA",
            signal="BUY",
            qty=80,
            SL=122.5,
            TP=134.0,
            status="pending",
            XAIReason="Fibonacci retracement level at 0.618 matches historic buying demand zones. Pre-market social sentiment indices show a +82% bullish index bias on news of cloud hardware expansions."
        ))
        db.add(ProposalModel(
            id="prop-3",
            symbol="TSLA",
            signal="SELL",
            qty=120,
            SL=183.0,
            TP=173.5,
            status="pending",
            XAIReason="Strong resistance verified at the 200 EMA on the 1-hour timeline. MACD histogram signals a bearish divergence crossover with rising sell volume, suggesting buyers exhaustion."
        ))
    if db.query(AuditLogModel).count() == 0:
        db.add(AuditLogModel(
            id="log-1",
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            symbol="QUANT",
            action_type="APPROVE",
            qty=150,
            price=151.60,
            status="SUCCESS",
            user="trader@kerdostat.com"
        ))
        db.add(AuditLogModel(
            id="log-2",
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            symbol="TSLA",
            action_type="REJECT",
            qty=120,
            price=183.00,
            status="SUCCESS",
            user="trader@kerdostat.com"
        ))
        db.add(AuditLogModel(
            id="log-3",
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            symbol="NVDA",
            action_type="HIJACK_EXECUTE",
            qty=100,
            price=125.50,
            status="SUCCESS",
            user="trader@kerdostat.com"
        ))
    if db.query(SystemStateModel).filter(SystemStateModel.key == "mode").count() == 0:
        db.add(SystemStateModel(key="mode", value="copilot"))
    db.commit()

import sys

scanner_task = None

async def run_symbol_scanner():
    SCAN_SYMBOLS = ["AAPL", "MSFT", "TSLA", "RELIANCE", "TCS", "INFY"]
    scanned_signals = {sym: "HOLD" for sym in SCAN_SYMBOLS}
    logger.info(f"Background scanner initialized for symbols: {SCAN_SYMBOLS}")
    try:
        while True:
            for symbol in SCAN_SYMBOLS:
                try:
                    candles = fetch_live_market_data(symbol, "1D")
                    if not candles or len(candles) < 30:
                        candles = generate_mock_ohlcv(symbol, "1D")
                    
                    from app.core.signal_engine import calculate_signals
                    result = calculate_signals(candles)
                    new_signal = result["signal"]
                    old_signal = scanned_signals.get(symbol, "HOLD")
                    
                    if new_signal != old_signal:
                        scanned_signals[symbol] = new_signal
                        logger.info(f"[Scanner] Signal changed for {symbol}: {old_signal} -> {new_signal}")
                        event = {
                            "event": "scanner_signal_changed",
                            "symbol": symbol,
                            "old_signal": old_signal,
                            "new_signal": new_signal,
                            "confidence_score": result.get("confidence_score", 0.50),
                            "xai_reason": result.get("xai_reason", "")
                        }
                        await manager.publish(event)
                except Exception as ex:
                    logger.error(f"Error scanning symbol {symbol}: {ex}")
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Background scanner task cancelled.")
    except Exception as ex:
        logger.error(f"Background scanner task crashed: {ex}")

@app.on_event("startup")
async def on_startup():
    global scanner_task
    if "pytest" not in sys.modules:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_db(db)
        finally:
            db.close()
    await manager.init_redis()
    scanner_task = asyncio.create_task(run_symbol_scanner())

@app.on_event("shutdown")
async def on_shutdown():
    global scanner_task
    if scanner_task:
        scanner_task.cancel()
        try:
            await scanner_task
        except asyncio.CancelledError:
            pass
    await manager.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT CONFIGS
JWT_SECRET = "supersecretkey_kerdostat_928173"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_jwt_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return {}

# Schemas
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ProposalCreateRequest(BaseModel):
    symbol: str
    signal: str
    qty: int
    SL: float
    TP: float
    XAIReason: Optional[str] = None

class ModeRequest(BaseModel):
    mode: str

class ActionRequest(BaseModel):
    action: str

class HijackRequest(BaseModel):
    symbol: str
    qty: int
    SL: float
    TP: float
    entry_price: float
    proposal_id: Optional[str] = None

@app.post("/auth/register")
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
    
    user_id = f"user-{db.query(UserModel).count() + 1}"
    new_user = UserModel(
        id=user_id,
        name=payload.name,
        email=email,
        password=payload.password
    )
    db.add(new_user)
    db.commit()
    logger.info(f"Registered new user: {email}")

    token = create_jwt_token({"sub": email, "name": payload.name})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )
    return {"id": user_id, "name": payload.name, "email": email}

@app.post("/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user or user.password != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    logger.info(f"User logged in: {email}")
    token = create_jwt_token({"sub": email, "name": user.name})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )
    return {"id": user.id, "name": user.name, "email": email}

@app.post("/auth/logout")
def logout(response: Response):
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        max_age=0,
        samesite="lax",
        secure=False
    )
    return {"status": "ok", "message": "Logged out successfully"}

@app.get("/auth/me")
def get_me(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing"
        )
    
    payload = decode_jwt_token(access_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    email = payload["sub"]
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return {"id": user.id, "name": user.name, "email": email}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = None
        self.pubsub = None
        self.listener_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_clients.append(connection)
        
        for client in disconnected_clients:
            self.disconnect(client)

    async def init_redis(self):
        if not self.redis_url:
            logger.info("REDIS_URL not set. Running in local WebSocket mode.")
            return

        try:
            self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info(f"Successfully connected to Redis at {self.redis_url}")
            
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("kerdostat-channel")
            logger.info("Subscribed to Redis channel 'kerdostat-channel'")
            
            self.listener_task = asyncio.create_task(self._redis_listener())
        except Exception as e:
            logger.error(f"Failed to initialize Redis Pub/Sub: {e}. Falling back to local mode.")
            self.redis_client = None

    async def _redis_listener(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        logger.info(f"Received message from Redis Pub/Sub: {data.get('event')}")
                        await self.broadcast(data)
                    except Exception as e:
                        logger.error(f"Error processing Redis Pub/Sub message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled.")
        except Exception as e:
            logger.error(f"Redis listener encountered error: {e}")

    async def publish(self, message: Dict[str, Any]):
        if self.redis_client:
            try:
                await self.redis_client.publish("kerdostat-channel", json.dumps(message))
                logger.info(f"Published message to Redis Pub/Sub: {message.get('event')}")
                return
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}. Falling back to local broadcast.")
        
        await self.broadcast(message)

    async def close(self):
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe("kerdostat-channel")
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "running", "service": "Kerdostat Platform Server"}

@app.get("/trade/account")
def get_trade_account():
    return alpaca_executor.get_account_info()

@app.get("/trade/positions")
def get_trade_positions():
    return alpaca_executor.get_positions()

# REST GET proposals
@app.get("/trade/proposals", response_model=List[Dict[str, Any]])
def get_proposals(db: Session = Depends(get_db)):
    props = db.query(ProposalModel).all()
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "signal": p.signal,
            "qty": p.qty,
            "SL": p.SL,
            "TP": p.TP,
            "status": p.status,
            "XAIReason": p.XAIReason
        } for p in props
    ]

# REST POST proposals (for creating proposals in tests)
@app.post("/trade/proposals", response_model=Dict[str, Any])
def create_proposal(payload: ProposalCreateRequest, db: Session = Depends(get_db)):
    prop_id = f"prop-{db.query(ProposalModel).count() + 1}"
    new_prop = ProposalModel(
        id=prop_id,
        symbol=payload.symbol.upper(),
        signal=payload.signal.upper(),
        qty=payload.qty,
        SL=payload.SL,
        TP=payload.TP,
        status="pending",
        XAIReason=payload.XAIReason or "Auto-generated proposal"
    )
    db.add(new_prop)
    db.commit()
    logger.info(f"Created proposal {prop_id} for symbol {new_prop.symbol}")
    return {
        "id": new_prop.id,
        "symbol": new_prop.symbol,
        "signal": new_prop.signal,
        "qty": new_prop.qty,
        "SL": new_prop.SL,
        "TP": new_prop.TP,
        "status": new_prop.status,
        "XAIReason": new_prop.XAIReason
    }

# REST GET/POST mode
@app.get("/trade/mode")
def get_system_mode(db: Session = Depends(get_db)):
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    mode = state.value if state else "copilot"
    return {"mode": mode}

@app.post("/trade/mode")
async def update_system_mode(payload: ModeRequest, db: Session = Depends(get_db)):
    mode = payload.mode.lower()
    if mode not in ["copilot", "autopilot"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be either 'copilot' or 'autopilot'"
        )
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    if not state:
        state = SystemStateModel(key="mode", value=mode)
        db.add(state)
    else:
        state.value = mode
    db.commit()
    logger.info(f"System mode updated to: {mode}")
    await manager.publish({"event": "mode_updated", "mode": mode})
    return {"mode": mode}

# REST PATCH proposals action
@app.patch("/trade/{proposal_id}/action")
async def update_proposal_action(proposal_id: str, payload: ActionRequest, db: Session = Depends(get_db)):
    action = payload.action.lower()
    if action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Action must be either 'approve' or 'reject'"
        )

    proposal = db.query(ProposalModel).filter(ProposalModel.id == proposal_id).first()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Proposal with ID {proposal_id} not found"
        )
    
    if proposal.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal.status}"
        )

    if action == "approve":
        candles = fetch_live_market_data(proposal.symbol, "1D")
        if not candles or len(candles) < 30:
            candles = generate_mock_ohlcv(proposal.symbol, "1D")
        current_price = candles[-1]["close"] if candles else proposal.SL * 1.02
        
        is_valid, reason = guardrail_engine.validate_trade(
            symbol=proposal.symbol,
            qty=proposal.qty,
            price=current_price,
            db=db,
            sl=proposal.SL
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Guardrail breach: {reason}"
            )

    # Update state
    proposal.status = "approved" if action == "approve" else "rejected"
    
    alpaca_order_id = None
    if action == "approve":
        try:
            executor = select_executor_by_symbol(proposal.symbol)
            order = executor.submit_order(
                symbol=proposal.symbol,
                qty=proposal.qty,
                side=proposal.signal.lower()
            )
            alpaca_order_id = getattr(order, "id", None)
            logger.info(f"Successfully placed order. ID: {alpaca_order_id}")
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Order execution failed: {str(e)}"
            )

    db.commit()
    logger.info(f"Proposal {proposal_id} updated state to: {proposal.status}")

    # Add audit log
    log_id = f"log-{db.query(AuditLogModel).count() + 1}"
    new_log = AuditLogModel(
        id=log_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol=proposal.symbol,
        action_type=action.upper(),
        qty=proposal.qty,
        price=proposal.SL,
        status="SUCCESS",
        user="trader@kerdostat.com"
    )
    db.add(new_log)
    db.commit()

    # Broadcast update to all connected WebSocket interfaces
    event = {
        "event": "proposal_updated",
        "proposal_id": proposal_id,
        "status": proposal.status,
        "symbol": proposal.symbol,
        "signal": proposal.signal,
        "alpaca_order_id": alpaca_order_id
    }
    await manager.publish(event)

    return {
        "id": proposal.id,
        "symbol": proposal.symbol,
        "signal": proposal.signal,
        "qty": proposal.qty,
        "SL": proposal.SL,
        "TP": proposal.TP,
        "status": proposal.status,
        "XAIReason": proposal.XAIReason
    }

# WebSocket path
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial success greeting
        await websocket.send_json({"event": "connected", "msg": "Kerdostat stream connected"})
        
        while True:
            # Maintain connection, handle incoming client packets (if any)
            data = await websocket.receive_text()
            # Respond to client messages or ping
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    rsi_values = [50.0] * len(prices)
    if len(prices) <= period:
        return rsi_values
    
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(0.0, change))
        losses.append(max(0.0, -change))
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi_values[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))
        
    for i in range(period + 1, len(prices)):
        change = prices[i] - prices[i-1]
        gain = max(0.0, change)
        loss = max(0.0, -change)
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi_values[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))
            
    return rsi_values

def fetch_live_market_data(symbol: str, range_val: str) -> Optional[List[Dict[str, Any]]]:
    ticker = symbol.upper()
    scale_factor = 1.0
    
    # Map common Indian stock tickers and indices
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
    params = {
        "range": yf_range,
        "interval": yf_interval
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(url, params=params, headers=headers, verify=False, timeout=5)
        if r.status_code != 200:
            # Fallback for Indian stocks (append .NS if it doesn't have an extension)
            if "." not in ticker and not ticker.startswith("^"):
                fallback_ticker = f"{ticker}.NS"
                fallback_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{fallback_ticker}"
                logger.info(f"Retrying with Indian NSE fallback symbol: {fallback_ticker}")
                r = requests.get(fallback_url, params=params, headers=headers, verify=False, timeout=5)
                if r.status_code == 200:
                    ticker = fallback_ticker
                else:
                    logger.warning(f"Yahoo API returned code {r.status_code} for {ticker}")
                    return None
            else:
                logger.warning(f"Yahoo API returned code {r.status_code} for {ticker}")
                return None
            
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
            return None
            
        candles = []
        for i in range(len(timestamps)):
            if (opens[i] is None or highs[i] is None or 
                lows[i] is None or closes[i] is None):
                continue
                
            dt = datetime.fromtimestamp(timestamps[i], timezone.utc)
            time_str = dt.strftime(time_format)
            
            candles.append({
                "time": time_str,
                "open": round(opens[i] * scale_factor, 2),
                "high": round(highs[i] * scale_factor, 2),
                "low": round(lows[i] * scale_factor, 2),
                "close": round(closes[i] * scale_factor, 2),
                "volume": int(volumes[i]) if (volumes[i] is not None) else 0
            })
            
        return candles
    except Exception as e:
        logger.warning(f"Failed to fetch live market data for {ticker}: {e}")
        return None

def deterministic_seed(symbol: str) -> int:
    return sum(ord(c) * (idx + 1) for idx, c in enumerate(symbol))

def generate_mock_ohlcv(symbol: str, range_val: str) -> List[Dict[str, Any]]:
    candles = []
    seed = deterministic_seed(symbol)
    rng = random.Random(seed)
    
    # Base price based on symbol name to make it consistent for the same symbol
    base_price = 100.0 + (sum(ord(c) for c in symbol) % 200)
    
    # Range parameters
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
        
        # Random walk
        change_pct = rng.uniform(-0.015, 0.015)
        o = price
        c = price * (1.0 + change_pct)
        h = max(o, c) * (1.0 + rng.uniform(0.0, 0.005))
        l = min(o, c) * (1.0 - rng.uniform(0.0, 0.005))
        
        # Ensure values are rounded and positive
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

@app.get("/market/ohlcv", response_model=List[Dict[str, Any]])
def get_market_ohlcv(symbol: str = "QUANT", range_val: str = Query("1D", alias="range")):
    # Try fetching live Yahoo data
    live_candles = fetch_live_market_data(symbol, range_val)
    if not live_candles or len(live_candles) < 30:
        live_candles = generate_mock_ohlcv(symbol, range_val)
        
    import pandas as pd
    import pandas_ta as ta

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

@app.get("/market/signal")
def get_market_signal(symbol: str = "QUANT", range_val: str = Query("1D", alias="range")):
    live_candles = fetch_live_market_data(symbol, range_val)
    if not live_candles or len(live_candles) < 30:
        live_candles = generate_mock_ohlcv(symbol, range_val)
    from app.core.signal_engine import calculate_signals
    return calculate_signals(live_candles)


@app.get("/trade/audit-logs", response_model=List[Dict[str, Any]])
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLogModel).all()
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp,
            "symbol": log.symbol,
            "action_type": log.action_type,
            "qty": log.qty,
            "price": log.price,
            "status": log.status,
            "user": log.user
        } for log in logs
    ]

# Override endpoint
@app.post("/trade/{id}/override")
async def execute_override(id: str, payload: HijackRequest, db: Session = Depends(get_db)):
    is_valid, reason = guardrail_engine.validate_trade(
        symbol=payload.symbol.upper(),
        qty=payload.qty,
        price=payload.entry_price,
        db=db,
        sl=payload.SL
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Guardrail breach: {reason}"
        )

    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    mode = state.value if state else "copilot"
    
    was_autopilot = (mode == "autopilot")
    if was_autopilot:
        if not state:
            state = SystemStateModel(key="mode", value="copilot")
            db.add(state)
        else:
            state.value = "copilot"
        db.commit()
        # Broadcast system mode change via ws
        await manager.publish({"event": "mode_updated", "mode": "copilot"})
        logger.info("Autopilot mode interrupted by override; system mode set to copilot.")
    
    # Add audit log
    log_id = f"log-{db.query(AuditLogModel).count() + 1}"
    new_log = AuditLogModel(
        id=log_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol=payload.symbol.upper(),
        action_type="HIJACK_EXECUTE",
        qty=payload.qty,
        price=payload.entry_price,
        status="SUCCESS",
        user="trader@kerdostat.com"
    )
    db.add(new_log)
    
    # Check if proposal exists by id, or matching symbol
    proposal = db.query(ProposalModel).filter(
        (ProposalModel.id == id) | (ProposalModel.symbol.ilike(f"%{payload.symbol}%"))
    ).first()
    
    alpaca_order_id = None
    try:
        side = "buy"
        if proposal and proposal.signal:
            side = proposal.signal.lower()
            
        executor = select_executor_by_symbol(payload.symbol)
        order = executor.submit_order(
            symbol=payload.symbol,
            qty=payload.qty,
            side=side,
            order_type="limit",
            price=payload.entry_price
        )
        alpaca_order_id = getattr(order, "id", None)
        logger.info(f"Successfully placed limit override order. ID: {alpaca_order_id}")
    except Exception as e:
        logger.error(f"Failed to place override order: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Override order execution failed: {str(e)}"
        )
    
    if proposal:
        if was_autopilot:
            proposal.status = "paused"
        else:
            proposal.status = "approved"
        proposal.qty = payload.qty
        proposal.SL = payload.SL
        proposal.TP = payload.TP
        
        logger.info(f"Override updated proposal {proposal.id}: status={proposal.status}")
        
        # Broadcast updated proposal via ws
        event = {
            "event": "proposal_updated",
            "proposal_id": proposal.id,
            "status": proposal.status,
            "symbol": proposal.symbol,
            "signal": proposal.signal,
            "alpaca_order_id": alpaca_order_id
        }
        await manager.publish(event)
    
    db.commit()
    return {"status": "success", "message": "Override executed and logged successfully"}

@app.post("/trade/hijack")
async def execute_hijack(payload: HijackRequest, db: Session = Depends(get_db)):
    return await execute_override(payload.proposal_id or "manual", payload, db)
