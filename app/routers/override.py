"""
app/routers/override.py
POST /trade/{id}/override — override SL/TP/quantity with guardrail checks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import TradeProposal, AuditLog, User
from app.schemas.schemas import TradeOverrideRequest, TradeOverrideResponse

router = APIRouter(prefix="/trade", tags=["Override"])

MAX_PER_TRADE_PCT = 5.0
SIMULATED_PORTFOLIO = 1000000


def validate_override(proposal: TradeProposal, override: TradeOverrideRequest):
    errors = []
    if override.quantity is not None:
        if override.quantity <= 0:
            errors.append("Quantity must be greater than 0.")
        trade_value = override.quantity * (proposal.risk_score * 100)
        trade_pct = (trade_value / SIMULATED_PORTFOLIO) * 100
        if trade_pct > MAX_PER_TRADE_PCT:
            errors.append(f"Quantity exceeds {MAX_PER_TRADE_PCT}% per-trade guardrail.")
    if override.stop_loss is not None:
        if override.stop_loss <= 0:
            errors.append("Stop loss must be a positive value.")
    if override.take_profit is not None:
        if override.take_profit <= 0:
            errors.append("Take profit must be a positive value.")
    if override.stop_loss and override.take_profit:
        if override.stop_loss >= override.take_profit:
            errors.append("Stop loss must be less than take profit.")
    if errors:
        raise HTTPException(status_code=422, detail={"guardrail_violations": errors})


@router.post(
    "/{proposal_id}/override",
    response_model=TradeOverrideResponse,
    summary="Override trade proposal SL/TP/quantity",
    description="""
## Trade Override
Allows a trader to modify Stop Loss, Take Profit, or Quantity before execution.

**Request body:**
- `quantity` — new quantity (optional)
- `stop_loss` — stop loss price (optional)
- `take_profit` — take profit price (optional)
- `reason` — mandatory reason for override

**Guardrail checks performed:**
- Quantity must be > 0
- Trade value must not exceed 5% portfolio guardrail
- Stop loss must be less than take profit
- Cannot override an already overridden proposal

**Responses:**
- `200` — Override applied successfully
- `400` — Already overridden
- `404` — Proposal not found
- `422` — Guardrail violation
- `401` — Invalid or expired token

**Requires JWT authentication.**
    """
)
def override_trade(
    proposal_id: int,
    override: TradeOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(TradeProposal).filter(
        TradeProposal.id == proposal_id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found")
    if proposal.status == "OVERRIDDEN":
        raise HTTPException(status_code=400, detail="This proposal has already been overridden.")

    validate_override(proposal, override)

    original_quantity = proposal.quantity
    if override.quantity is not None:
        proposal.quantity = override.quantity
    if override.stop_loss is not None:
        proposal.stop_loss = override.stop_loss
    if override.take_profit is not None:
        proposal.take_profit = override.take_profit

    proposal.status = "OVERRIDDEN"
    db.commit()
    db.refresh(proposal)

    log_entry = AuditLog(
        trade_proposal_id=proposal_id,
        action_taken="OVERRIDE",
        decision_by=current_user.username,
        reason=override.reason
    )
    db.add(log_entry)
    db.commit()

    return TradeOverrideResponse(
        proposal_id=proposal.id,
        status=proposal.status,
        original_quantity=original_quantity,
        new_quantity=proposal.quantity,
        stop_loss=proposal.stop_loss,
        take_profit=proposal.take_profit,
        reason=override.reason,
        overridden_by=current_user.username,
        timestamp=datetime.now(timezone.utc)
    )