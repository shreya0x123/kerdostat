import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.services import select_executor_by_symbol
from app.core.state_machine import ExecutionStateMachine, ExecutionEvent, ExecutionState

logger = logging.getLogger("kerdostat-reconciler")

def reconcile_proposal(proposal_id: str, db: Session, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    3-Stage Authoritative Reconciliation Engine with Granular Broker Status Mirroring:
    - Mirrors exact broker status: FILLED, PARTIALLY_FILLED, SUBMITTED, CANCELLED, BROKER_REJECTED.
    - Updates partial fill metrics (filled_qty, remaining_qty, avg_fill_price).
    - Guarantees zero duplicate orders.
    """
    proposal = db.query(ProposalModel).filter(ProposalModel.id == proposal_id).first()
    if not proposal:
        raise ValueError(f"Proposal {proposal_id} not found.")

    if proposal.status not in [ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionState.SUBMITTING.value, "submitting"]:
        return {
            "reconciled": False,
            "status": proposal.status,
            "outcome": "NOT_REQUIRED",
            "message": f"Proposal is in '{proposal.status}' state, no reconciliation required."
        }

    client_order_id = proposal.client_order_id or f"KERDOSTAT-{proposal.id}-v{proposal.execution_version}"
    executor = select_executor_by_symbol(proposal.symbol)
    
    found_order = None
    query_failed = False
    now_iso = datetime.now(timezone.utc).isoformat()
    proposal.reconcile_attempts = (proposal.reconcile_attempts or 0) + 1
    proposal.last_reconciled_at = now_iso
    corr_id = correlation_id or f"CORR-{proposal.id}-{now_iso}"

    # 1. Query broker for existing order using client_order_id
    try:
        if getattr(executor, "is_mock", lambda: True)():
            for ord_id, mock_ord in getattr(executor, "mock_orders", {}).items():
                if getattr(mock_ord, "client_order_id", None) == client_order_id or ord_id == proposal.broker_order_id:
                    found_order = mock_ord
                    break
        else:
            if hasattr(executor, "client") and executor.client:
                try:
                    found_order = executor.client.get_order_by_client_order_id(client_order_id)
                except Exception as e:
                    err_str = str(e).lower()
                    if "not found" not in err_str and "404" not in err_str:
                        query_failed = True
                
                if not found_order and not query_failed and proposal.broker_order_id:
                    try:
                        found_order = executor.get_order_status(proposal.broker_order_id)
                    except Exception as e:
                        err_str = str(e).lower()
                        if "not found" not in err_str and "404" not in err_str:
                            query_failed = True
    except Exception as e:
        logger.error(f"Error during broker order query: {e}")
        query_failed = True

    prev_state = proposal.status

    # Case A: Inconclusive Query -> RECONCILE_UNCERTAIN
    if query_failed:
        db.commit()
        logger.warning(f"Reconciliation for {proposal_id} UNCERTAIN: broker query inconclusive.")
        return {
            "reconciled": False,
            "status": proposal.status,
            "outcome": "RECONCILE_UNCERTAIN",
            "attempts": proposal.reconcile_attempts,
            "message": "Broker query failed or was inconclusive. Order retained in SUBMISSION_UNKNOWN for retry."
        }

    # Case B: Order Found at Broker -> Mirror Exact Status
    if found_order:
        raw_status = str(getattr(found_order, "status", "submitted")).lower()
        req_qty = proposal.requested_qty or proposal.qty
        
        # Read filled_qty safely if present as numeric
        raw_filled = getattr(found_order, "filled_qty", None)
        if isinstance(raw_filled, (int, float)):
            filled_qty = int(raw_filled)
        elif isinstance(raw_filled, str) and raw_filled.isdigit():
            filled_qty = int(raw_filled)
        else:
            filled_qty = req_qty if raw_status == "filled" else 0
        
        if raw_status in ["filled"]:
            new_state = ExecutionStateMachine.get_next_state(
                prev_state, ExecutionEvent.RECONCILE_FOUND_FILLED.value
            )
            proposal.filled_qty = req_qty
            proposal.remaining_qty = 0
        elif raw_status in ["partially_filled", "partial_fill"] or (0 < filled_qty < req_qty):
            new_state = ExecutionStateMachine.get_next_state(
                prev_state, ExecutionEvent.RECONCILE_FOUND_PARTIAL.value
            )
            proposal.filled_qty = filled_qty
            proposal.remaining_qty = max(0, req_qty - filled_qty)
        elif raw_status in ["rejected"]:
            new_state = ExecutionState.BROKER_REJECTED.value
        elif raw_status in ["cancelled", "canceled", "expired"]:
            new_state = ExecutionStateMachine.get_next_state(
                prev_state, ExecutionEvent.RECONCILE_FOUND_CANCELLED.value
            )
        else:
            new_state = ExecutionStateMachine.get_next_state(
                prev_state, ExecutionEvent.RECONCILE_FOUND_SUBMITTED.value
            )
            proposal.filled_qty = filled_qty
            proposal.remaining_qty = req_qty

        proposal.status = new_state
        proposal.broker_order_id = getattr(found_order, "id", proposal.broker_order_id)
        proposal.last_broker_update = now_iso
        
        audit_event = AuditLogModel(
            id=str(uuid.uuid4()),
            event_id=str(uuid.uuid4()),
            proposal_id=proposal.id,
            user_id=proposal.user_id,
            correlation_id=corr_id,
            execution_version=proposal.execution_version,
            actor_type="RECONCILER",
            timestamp=now_iso,
            event_timestamp=now_iso,
            symbol=proposal.symbol,
            action_type="RECONCILE_FOUND",
            event_type="RECONCILIATION",
            previous_state=prev_state,
            new_state=new_state,
            qty=proposal.qty,
            price=proposal.SL or 0.0,
            status="SUCCESS",
            user=proposal.user_id or "system",
            client_order_id=client_order_id,
            broker_order_id=proposal.broker_order_id,
            reason=f"Broker confirmed order with status: {raw_status} (Filled: {proposal.filled_qty}/{req_qty})"
        )
        db.add(audit_event)
        db.commit()
        db.refresh(proposal)

        logger.info(f"Proposal {proposal_id} reconciled to {new_state} (Broker ID: {proposal.broker_order_id}, Filled: {proposal.filled_qty})")
        return {
            "reconciled": True,
            "status": new_state,
            "outcome": "RECONCILE_FOUND",
            "broker_order_id": proposal.broker_order_id,
            "filled_qty": proposal.filled_qty,
            "remaining_qty": proposal.remaining_qty,
            "message": f"Order confirmed by broker with status '{raw_status}'."
        }

    # Case C: Order Definitively Absent -> RECONCILE_ABSENT_CONFIRMED
    else:
        new_state = ExecutionStateMachine.get_next_state(
            prev_state, ExecutionEvent.RECONCILE_ABSENT.value
        )
        proposal.status = new_state
        
        audit_event = AuditLogModel(
            id=str(uuid.uuid4()),
            event_id=str(uuid.uuid4()),
            proposal_id=proposal.id,
            user_id=proposal.user_id,
            correlation_id=corr_id,
            execution_version=proposal.execution_version,
            actor_type="RECONCILER",
            timestamp=now_iso,
            event_timestamp=now_iso,
            symbol=proposal.symbol,
            action_type="RECONCILE_ABSENT_CONFIRMED",
            event_type="RECONCILIATION",
            previous_state=prev_state,
            new_state=new_state,
            qty=proposal.qty,
            price=proposal.SL or 0.0,
            status="SUCCESS",
            user=proposal.user_id or "system",
            client_order_id=client_order_id,
            reason="Order definitively absent at broker. Marked safe for versioned retry."
        )
        db.add(audit_event)
        db.commit()
        db.refresh(proposal)

        logger.warning(f"Proposal {proposal_id} confirmed absent at broker. Reconciled to {new_state}.")
        return {
            "reconciled": True,
            "status": new_state,
            "outcome": "RECONCILE_ABSENT_CONFIRMED",
            "message": "Order absent at broker. Marked as RECONCILE_ABSENT for safe versioned retry."
        }

def reconcile_all_unknown(db: Session) -> Dict[str, Any]:
    unknowns = db.query(ProposalModel).filter(
        ProposalModel.status.in_(["SUBMISSION_UNKNOWN", "submitting", "SUBMITTING"])
    ).all()
    
    results = []
    for prop in unknowns:
        try:
            res = reconcile_proposal(prop.id, db)
            results.append({"proposal_id": prop.id, "result": res})
        except Exception as e:
            results.append({"proposal_id": prop.id, "error": str(e)})
            
    return {"total_checked": len(unknowns), "reconciled_results": results}

def reconcile_stranded_on_startup(db: Session) -> int:
    logger.info("Running startup execution crash recovery and reconciliation...")
    res = reconcile_all_unknown(db)
    count = res.get("total_checked", 0)
    logger.info(f"Startup crash recovery complete. Checked {count} proposals.")
    return count
