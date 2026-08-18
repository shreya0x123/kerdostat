import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core imports
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, get_db
from app.core.logger import logger
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    get_current_user,
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.websocket import manager, ConnectionManager

# Models
from app.models.user import UserModel
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.models.state import SystemStateModel

# Schemas
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from app.schemas.trade import ProposalCreateRequest, ActionRequest, ModeRequest, HijackRequest, OverrideRequest

# Services
from app.services import (
    alpaca_executor,
    fyers_executor,
    guardrail_engine,
    select_executor_by_symbol,
    fetch_live_market_data,
    generate_mock_ohlcv,
    get_alpaca_assets,
    MOCK_ASSETS
)
from app.services.scanner import seed_db, run_symbol_scanner

# Routers
from app.routers.auth import router as auth_router
from app.routers.trade import router as trade_router
from app.routers.market import router as market_router
from app.routers.health import router as health_router
from app.routers.ws import router as ws_router

scanner_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scanner_task
    # Startup
    if "pytest" not in sys.modules:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_db(db)
            from app.services.reconciliation import reconcile_stranded_on_startup
            reconcile_stranded_on_startup(db)
        finally:
            db.close()
        scanner_task = asyncio.create_task(run_symbol_scanner())
        logger.info("Kerdostat backend application startup complete.")
    yield
    # Shutdown
    if scanner_task:
        scanner_task.cancel()
        try:
            await scanner_task
        except asyncio.CancelledError:
            pass
    logger.info("Kerdostat backend application shutdown complete.")

app = FastAPI(
    title="Kerdostat Live Trading API",
    version="1.0.0",
    description="Human-in-the-Loop Algorithmic Trading Workspace API",
    lifespan=lifespan
)

# Dynamic CORS Middleware Configuration
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_origins:
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(trade_router)
app.include_router(market_router)
app.include_router(ws_router)

# Root-level exports for backwards compatibility with tests and scripts
__all__ = [
    "app",
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "UserModel",
    "ProposalModel",
    "AuditLogModel",
    "SystemStateModel",
    "alpaca_executor",
    "fyers_executor",
    "guardrail_engine",
    "manager",
    "ConnectionManager",
    "create_jwt_token",
    "decode_jwt_token",
    "get_current_user",
    "seed_db",
    "select_executor_by_symbol",
    "fetch_live_market_data",
    "generate_mock_ohlcv",
    "get_alpaca_assets",
    "MOCK_ASSETS"
]
