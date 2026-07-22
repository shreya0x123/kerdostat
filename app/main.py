import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.models import models
from app.api.routes import health
from app.routers import version, auth, trade, audit, signal, user, override, market, websocket, guardrails, admin

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Kerdostat starting (env=%s) ===", settings.APP_ENV)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    yield
    logger.info("=== Kerdostat shutting down ===")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dual-mode mixed-initiative algorithmic trading framework with XDI.",
    lifespan=lifespan,
)

# ── Rate Limit Handler ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Security Headers Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Error Handling Middleware ─────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    from starlette.exceptions import HTTPException as StarletteHTTPException
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": str(exc.detail) if hasattr(exc, 'detail') else f"Route {request.url.path} does not exist",
            "status_code": 404
        }
    )
@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }
    )

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={
            "error": "Unauthorized",
            "message": "Invalid or expired token",
            "status_code": 401
        }
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(version.router)
app.include_router(auth.router)
app.include_router(trade.router)
app.include_router(audit.router)
app.include_router(signal.router)
app.include_router(user.router)
app.include_router(override.router)
app.include_router(market.router)
app.include_router(websocket.router)
app.include_router(guardrails.router)
app.include_router(admin.router)

# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION} is running."}