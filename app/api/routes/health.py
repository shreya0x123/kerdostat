"""
kerdostat/app/api/routes/health.py
GET /health          — basic liveness probe
GET /health/broker   — Alpaca connectivity smoke test
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.broker import broker_service, AccountSnapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


class LivenessResponse(BaseModel):
    status: str
    version: str


class BrokerHealthResponse(BaseModel):
    status: str
    account_number: str
    account_status: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    currency: str
    paper_trading: bool


@router.get(
    "/",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="""
## Liveness Probe
Returns HTTP 200 immediately with no external dependencies checked.
Used by load balancers and monitoring tools to verify the server is alive.

**No authentication required.**
    """
)
def liveness():
    from app.core.config import settings
    return LivenessResponse(status="ok", version=settings.APP_VERSION)


@router.get(
    "/broker",
    response_model=BrokerHealthResponse,
    summary="Alpaca broker connectivity check",
    description="""
## Broker Health Check
Calls Alpaca GET /v2/account to verify broker connectivity.

**Responses:**
- `200` — Connected, returns account snapshot
- `502` — Alpaca API error
- `503` — Credentials not configured

**No authentication required.**
    """
)
def broker_health():
    from app.core.config import settings
    if not settings.is_alpaca_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Alpaca credentials not configured. "
                "Add ALPACA_API_KEY and ALPACA_SECRET_KEY to your .env file."
            ),
        )
    try:
        snapshot: AccountSnapshot = broker_service.smoke_test()
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Broker smoke test failed")
        raise HTTPException(status_code=502, detail=f"Alpaca error: {exc}")

    return BrokerHealthResponse(
        status="connected",
        account_number=snapshot.account_number,
        account_status=snapshot.status,
        equity=snapshot.equity,
        cash=snapshot.cash,
        buying_power=snapshot.buying_power,
        portfolio_value=snapshot.portfolio_value,
        currency=snapshot.currency,
        paper_trading=snapshot.paper_trading,
    )