"""
app/services/autopilot.py
Autopilot Service (HOTL)
Handles automated evaluation and execution of trade proposals when user mode is AUTOPILOT.
"""

import logging
from sqlalchemy.orm import Session
from app.models.models import TradeProposal, AuditLog, User

logger = logging.getLogger(__name__)

SIMULATED_PORTFOLIO = 1000000
MAX_PER_TRADE_PCT = 5.0
MAX_RISK_SCORE = 7.0


def evaluate_and_execute_autopilot(
    proposal: TradeProposal,
    user: User,
    db: Session
) -> dict:
    """
    Evaluates guardrails for a trade proposal in AUTOPILOT mode.
    If guardrails pass, executes trade via broker_service and logs to audit trail.
    If guardrails fail, blocks auto-execution and logs guardrail breach.
    """
    from app.services.broker import broker_service

    logger.info(f"[AUTOPILOT] Evaluating proposal ID={proposal.id} for user={user.username}")

    # ── Guardrail check ──────────────────────────────────────────────────────
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
        violation_msg = " | ".join(guardrail_violations)
        logger.warning(f"[AUTOPILOT] Guardrail hit for proposal ID={proposal.id}: {violation_msg}")

        log_entry = AuditLog(
            trade_proposal_id=proposal.id,
            action_taken="GUARDRAIL_BLOCKED",
            decision_by=user.username,
            reason=violation_msg,
            mode="AUTOPILOT",
            guardrail_hit=violation_msg
        )
        db.add(log_entry)
        db.commit()

        return {
            "auto_executed": False,
            "status": proposal.status,
            "reason": "Guardrail violation in Autopilot mode",
            "violations": guardrail_violations
        }

    # ── Execute trade via Broker Service ────────────────────────────────────
    try:
        order_id = None
        try:
            order = broker_service.client.submit_order(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=proposal.action.lower(),
                type="market",
                time_in_force="day"
            )
            order_id = order.id
        except Exception as e:
            logger.info(f"[AUTOPILOT] Broker paper trade simulated (live credentials skipped/mocked): {e}")
            order_id = f"sim-autopilot-{proposal.id}"

        proposal.status = "EXECUTED"
        db.commit()
        db.refresh(proposal)

        log_entry = AuditLog(
            trade_proposal_id=proposal.id,
            action_taken="AUTO_EXECUTED",
            decision_by=user.username,
            reason=f"Autopilot auto-executed order. Order ID: {order_id}",
            mode="AUTOPILOT"
        )
        db.add(log_entry)
        db.commit()

        # ── Day 11: Emit WebSocket event for auto-execution ───────────────────
        ws_event = {
            "type": "autopilot_executed",
            "proposal_id": proposal.id,
            "symbol": proposal.symbol,
            "action": proposal.action,
            "quantity": proposal.quantity,
            "order_id": order_id,
            "mode": "AUTOPILOT",
        }
        try:
            import asyncio
            from app.routers.websocket import manager
            # Fire-and-forget broadcast (non-blocking; manager handles disconnects)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(manager.broadcast(ws_event))
            else:
                loop.run_until_complete(manager.broadcast(ws_event))
        except Exception as ws_exc:
            # WebSocket broadcast failure must never block trade execution
            logger.warning("[AUTOPILOT] WebSocket broadcast failed (non-fatal): %s", ws_exc)

        return {
            "auto_executed": True,
            "status": "EXECUTED",
            "order_id": order_id,
            "symbol": proposal.symbol,
            "action": proposal.action,
            "quantity": proposal.quantity
        }

    except Exception as exc:
        logger.error(f"[AUTOPILOT] Execution exception for proposal ID={proposal.id}: {exc}")
        return {
            "auto_executed": False,
            "status": proposal.status,
            "error": str(exc)
        }

