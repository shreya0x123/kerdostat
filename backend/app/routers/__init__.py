from app.routers.auth import router as auth_router
from app.routers.trade import router as trade_router
from app.routers.market import router as market_router
from app.routers.health import router as health_router
from app.routers.ws import router as ws_router

__all__ = [
    "auth_router",
    "trade_router",
    "market_router",
    "health_router",
    "ws_router"
]
