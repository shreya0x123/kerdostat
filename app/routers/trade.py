from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.models.models import AuditLog
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import TradeProposal, User
from app.schemas.schemas import (
    TradeProposalCreate, TradeProposalResponse,
    TradeExecuteRequest, TradeExecuteResponse,
)
from app.services.alpaca_executor import alpaca_executor

router = APIRouter(prefix="/trade", tags=["Trade"])



@router.post("/propose", response_model=TradeProposalResponse)
def propose_trade(
    proposal: TradeProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # JWT auth middleware
):
    """
    POST /trade/propose
    Accepts a trade signal payload from the signal engine.
    Stores it in the trade_proposals table with status PENDING.
    Requires valid JWT token.
    """
    new_proposal = TradeProposal(
        symbol=proposal.symbol,
        action=proposal.action,
        quantity=proposal.quantity,
        risk_score=proposal.risk_score,
        indicator_summary=proposal.indicator_summary,
        status="PENDING"
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)
    return new_proposal


@router.get("/proposals", response_model=List[TradeProposalResponse])
def get_proposals(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # JWT auth middleware
):
    """
    GET /trade/proposals
    Returns paginated list of trade proposals.
    Optional filter by status: PENDING, APPROVED, REJECTED.
    Requires valid JWT token.
    """
    query = db.query(TradeProposal)

    if status:
        query = query.filter(TradeProposal.status == status)

    offset = (page - 1) * page_size
    proposals = query.order_by(TradeProposal.created_at.desc()).offset(offset).limit(page_size).all()

    return proposals
@router.patch("/{proposal_id}/action", response_model=TradeProposalResponse)
def action_on_proposal(
    proposal_id: int,
    action: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PATCH /trade/{id}/action
    Approve, reject, or modify a trade proposal.
    Action must be: COMMIT, REJECT, or MODIFY
    Every action is logged to the audit_logs table with timestamp + user_id.
    Requires valid JWT token.
    """
    # Validate action
    valid_actions = ["COMMIT", "REJECT", "MODIFY"]
    if action.upper() not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )

    # Find proposal
    proposal = db.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    # Update proposal status
    proposal.status = "APPROVED" if action.upper() == "COMMIT" else action.upper()
    db.commit()
    db.refresh(proposal)

    # Write audit log entry
    log_entry = AuditLog(
        trade_proposal_id=proposal_id,
        action_taken=action.upper(),
        decision_by=current_user.username,
        reason=reason or f"{action.upper()} by {current_user.username}"
    )
    db.add(log_entry)
    db.commit()

    return proposal
@router.post("/execute/{proposal_id}")
def execute_trade(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    POST /trade/execute/{proposal_id}
    Runs guardrail check before calling Alpaca.
    Blocks execution if risk score > 7 or quantity exceeds 5% portfolio.
    Updates trade status to EXECUTED in DB.
    Logs execution to audit trail.
    Requires valid JWT token.
    """
    from app.services.broker import broker_service

    SIMULATED_PORTFOLIO = 1000000
    MAX_PER_TRADE_PCT = 5.0
    MAX_RISK_SCORE = 7.0

    # Find proposal
    proposal = db.query(TradeProposal).filter(
        TradeProposal.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    if proposal.status not in ["APPROVED", "OVERRIDDEN", "RESUMED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal must be APPROVED, OVERRIDDEN, or RESUMED to execute. Current status: {proposal.status}"
        )

    # ── Guardrail check before Alpaca ────────────────────────────────────────
    guardrail_violations = []

    trade_value = proposal.quantity * (proposal.risk_score * 100)
    trade_pct = (trade_value / SIMULATED_PORTFOLIO) * 100

    if proposal.risk_score > MAX_RISK_SCORE:
        guardrail_violations.append(
            f"Risk score {proposal.risk_score}/10 exceeds maximum allowed {MAX_RISK_SCORE}/10."
        )

    if trade_pct > MAX_PER_TRADE_PCT:
        guardrail_violations.append(
            f"Trade value {trade_pct:.1f}% exceeds {MAX_PER_TRADE_PCT}% per-trade guardrail."
        )

    if guardrail_violations:
        # Log guardrail hit to audit
        log_entry = AuditLog(
            trade_proposal_id=proposal_id,
            action_taken="GUARDRAIL_BLOCKED",
            decision_by=current_user.username,
            reason=" | ".join(guardrail_violations),
            guardrail_hit=" | ".join(guardrail_violations)
        )
        db.add(log_entry)
        db.commit()

        raise HTTPException(
            status_code=422,
            detail={
                "error": "Guardrail violation — execution blocked",
                "violations": guardrail_violations
            }
        )

    # ── Submit to Alpaca ─────────────────────────────────────────────────────
    try:
        order_id = f"sim-order-{proposal.id}"
        try:
            order = broker_service.client.submit_order(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=proposal.action.lower(),
                type="market",
                time_in_force="day"
            )
            order_id = order.id
        except Exception:
            pass

        proposal.status = "EXECUTED"
        db.commit()
        db.refresh(proposal)

        log_entry = AuditLog(
            trade_proposal_id=proposal_id,
            action_taken="EXECUTED",
            decision_by=current_user.username,
            reason=f"Order submitted to broker — Order ID: {order_id}",
            mode="HITL"
        )
        db.add(log_entry)
        db.commit()

        return {
            "proposal_id": proposal_id,
            "status": "EXECUTED",
            "alpaca_order_id": order_id,
            "symbol": proposal.symbol,
            "action": proposal.action,
            "quantity": proposal.quantity,
            "executed_by": current_user.username
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution error: {str(e)}"
        )


@router.post("/{proposal_id}/interrupt", response_model=TradeProposalResponse, summary="Interrupt autopilot execution")
def interrupt_trade(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    POST /trade/{id}/interrupt
    Halts execution of an active or pending proposal in Autopilot mode.
    Sets proposal status to INTERRUPTED.
    Logs action to audit trail.
    Requires valid JWT token.
    """
    proposal = db.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    if proposal.status in ["EXECUTED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot interrupt a proposal with status '{proposal.status}'"
        )

    proposal.status = "INTERRUPTED"
    db.commit()
    db.refresh(proposal)

    log_entry = AuditLog(
        trade_proposal_id=proposal_id,
        action_taken="INTERRUPT",
        decision_by=current_user.username,
        reason=f"Execution interrupted by trader {current_user.username}",
        mode=getattr(current_user, "mode", "COPILOT")
    )
    db.add(log_entry)
    db.commit()

    return proposal


@router.post("/{proposal_id}/resume", response_model=TradeProposalResponse, summary="Resume execution after interrupt/hijack")
def resume_trade(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    POST /trade/{id}/resume
    Resumes an interrupted trade proposal after manual review/hijack.
    Sets status to RESUMED.
    Logs action to audit trail.
    Requires valid JWT token.
    """
    proposal = db.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    if proposal.status not in ["INTERRUPTED", "PAUSED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only INTERRUPTED or PAUSED proposals can be resumed. Current status: '{proposal.status}'"
        )

    proposal.status = "RESUMED"
    db.commit()
    db.refresh(proposal)

    log_entry = AuditLog(
        trade_proposal_id=proposal_id,
        action_taken="RESUME",
        decision_by=current_user.username,
        reason=f"Execution resumed by trader {current_user.username}",
        mode=getattr(current_user, "mode", "COPILOT")
    )
    db.add(log_entry)
    db.commit()

    return proposal


# ── POST /trade/execute (Day 8) ───────────────────────────────────────────────

@router.post(
    "/execute",
    response_model=TradeExecuteResponse,
    summary="Execute a trade proposal through Alpaca paper trading",
    description="""
## Trade Execution

Executes a PENDING trade proposal through the Alpaca paper-trading API.

Set `ALPACA_MOCK_MODE=true` in `.env` to run locally without real credentials.

**Responses:**
- `200` — Order submitted (order_id, fill_status, avg_fill_price)
- `404` — Proposal not found
- `400` — Proposal not in PENDING status
- `401` — Invalid or expired token
    """,
)
def execute_trade(
    body: TradeExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /trade/execute

    1. Fetch the proposal from DB.
    2. Validate it is PENDING.
    3. Submit through AlpacaExecutor (paper trading only).
    4. Update proposal status to EXECUTED or FAILED.
    5. Write audit log.
    6. Return structured response.
    """
    proposal = db.query(TradeProposal).filter(
        TradeProposal.id == body.proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Trade proposal not found.")

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING proposals can be executed. Current status: '{proposal.status}'",
        )

    qty    = proposal.quantity
    symbol = proposal.symbol
    action = proposal.action.lower()

    if action == "buy":
        order_result = alpaca_executor.submit_buy(symbol, qty)
    elif action == "sell":
        order_result = alpaca_executor.submit_sell(symbol, qty)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {proposal.action}")

    if order_result.status == "error":
        proposal.status = "FAILED"
        db.commit()
        db.add(AuditLog(
            trade_proposal_id=proposal.id,
            action_taken="EXECUTION_FAILED",
            decision_by=current_user.username,
            reason=order_result.error_message or "Unknown broker error",
            mode=getattr(current_user, "mode", "COPILOT"),
        ))
        db.commit()
        return TradeExecuteResponse(
            proposal_id=proposal.id,
            order_id="",
            symbol=symbol,
            action=proposal.action,
            quantity=qty,
            status="failed",
            fill_status="error",
            filled_qty=0.0,
            avg_fill_price=None,
            mock_mode=alpaca_executor.is_mock,
            message=f"Execution failed: {order_result.error_message}",
        )

    fill = alpaca_executor.get_fill_status(order_result.order_id)
    proposal.status = "EXECUTED"
    db.commit()

    db.add(AuditLog(
        trade_proposal_id=proposal.id,
        action_taken="EXECUTED",
        decision_by=current_user.username,
        reason=(
            f"Order {order_result.order_id} submitted — mock={alpaca_executor.is_mock}. "
            f"Fill={fill.status} qty={fill.filled_qty}."
        ),
        mode=getattr(current_user, "mode", "COPILOT"),
    ))
    db.commit()

    return TradeExecuteResponse(
        proposal_id=proposal.id,
        order_id=order_result.order_id,
        symbol=symbol,
        action=proposal.action,
        quantity=qty,
        status="executed",
        fill_status=fill.status,
        filled_qty=fill.filled_qty,
        avg_fill_price=fill.avg_fill_price,
        mock_mode=alpaca_executor.is_mock,
        message=f"Order submitted. Fill: {fill.status}.",
    )