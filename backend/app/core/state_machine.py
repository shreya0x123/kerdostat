from enum import Enum
from typing import Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger("kerdostat-state-machine")

class ExecutionState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    BROKER_REJECTED = "BROKER_REJECTED"
    BROKER_ERROR = "broker_error"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    RECONCILE_ABSENT = "RECONCILE_ABSENT"
    PAUSED = "PAUSED"
    INTERRUPTED = "INTERRUPTED"
    REJECTED = "rejected"
    CANCELLED = "CANCELLED"

class ExecutionEvent(str, Enum):
    SUBMIT = "SUBMIT"
    BROKER_ACK = "BROKER_ACK"
    BROKER_FILL = "BROKER_FILL"
    BROKER_PARTIAL_FILL = "BROKER_PARTIAL_FILL"
    BROKER_REJECT = "BROKER_REJECT"
    BROKER_TIMEOUT = "BROKER_TIMEOUT"
    BROKER_ERROR = "BROKER_ERROR"
    RECONCILE_FOUND_SUBMITTED = "RECONCILE_FOUND_SUBMITTED"
    RECONCILE_FOUND_PARTIAL = "RECONCILE_FOUND_PARTIAL"
    RECONCILE_FOUND_FILLED = "RECONCILE_FOUND_FILLED"
    RECONCILE_FOUND_CANCELLED = "RECONCILE_FOUND_CANCELLED"
    RECONCILE_ABSENT = "RECONCILE_ABSENT"
    RECONCILE_UNCERTAIN = "RECONCILE_UNCERTAIN"
    REJECT = "REJECT"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CANCEL = "CANCEL"

class IllegalStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    pass

# Formal state transition matrix: (CurrentState, Event) -> NextState
TRANSITION_MATRIX: Dict[Tuple[str, str], str] = {
    # Pending transitions
    (ExecutionState.PENDING.value, ExecutionEvent.SUBMIT.value): ExecutionState.SUBMITTING.value,
    (ExecutionState.PENDING.value, ExecutionEvent.REJECT.value): ExecutionState.REJECTED.value,
    (ExecutionState.PENDING.value, ExecutionEvent.PAUSE.value): ExecutionState.PAUSED.value,
    (ExecutionState.PENDING.value, ExecutionEvent.CANCEL.value): ExecutionState.CANCELLED.value,

    # Paused / Interrupted transitions
    (ExecutionState.PAUSED.value, ExecutionEvent.SUBMIT.value): ExecutionState.SUBMITTING.value,
    (ExecutionState.PAUSED.value, ExecutionEvent.RESUME.value): ExecutionState.PENDING.value,
    (ExecutionState.PAUSED.value, ExecutionEvent.REJECT.value): ExecutionState.REJECTED.value,
    (ExecutionState.INTERRUPTED.value, ExecutionEvent.SUBMIT.value): ExecutionState.SUBMITTING.value,
    (ExecutionState.INTERRUPTED.value, ExecutionEvent.RESUME.value): ExecutionState.PENDING.value,
    (ExecutionState.INTERRUPTED.value, ExecutionEvent.REJECT.value): ExecutionState.REJECTED.value,

    # Submitting transitions
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_ACK.value): ExecutionState.APPROVED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_FILL.value): ExecutionState.FILLED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_PARTIAL_FILL.value): ExecutionState.PARTIALLY_FILLED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_REJECT.value): ExecutionState.BROKER_REJECTED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_TIMEOUT.value): ExecutionState.SUBMISSION_UNKNOWN.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.BROKER_ERROR.value): ExecutionState.BROKER_ERROR.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_FOUND_FILLED.value): ExecutionState.FILLED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_FOUND_PARTIAL.value): ExecutionState.PARTIALLY_FILLED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_FOUND_SUBMITTED.value): ExecutionState.SUBMITTED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_FOUND_CANCELLED.value): ExecutionState.CANCELLED.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_ABSENT.value): ExecutionState.RECONCILE_ABSENT.value,
    (ExecutionState.SUBMITTING.value, ExecutionEvent.RECONCILE_UNCERTAIN.value): ExecutionState.SUBMISSION_UNKNOWN.value,

    # Approved / Submitted transitions
    (ExecutionState.APPROVED.value, ExecutionEvent.BROKER_FILL.value): ExecutionState.FILLED.value,
    (ExecutionState.APPROVED.value, ExecutionEvent.BROKER_PARTIAL_FILL.value): ExecutionState.PARTIALLY_FILLED.value,
    (ExecutionState.SUBMITTED.value, ExecutionEvent.BROKER_FILL.value): ExecutionState.FILLED.value,
    (ExecutionState.SUBMITTED.value, ExecutionEvent.BROKER_PARTIAL_FILL.value): ExecutionState.PARTIALLY_FILLED.value,
    (ExecutionState.APPROVED.value, ExecutionEvent.CANCEL.value): ExecutionState.CANCELLED.value,
    (ExecutionState.SUBMITTED.value, ExecutionEvent.CANCEL.value): ExecutionState.CANCELLED.value,

    # Partially Filled transitions
    (ExecutionState.PARTIALLY_FILLED.value, ExecutionEvent.BROKER_FILL.value): ExecutionState.FILLED.value,
    (ExecutionState.PARTIALLY_FILLED.value, ExecutionEvent.CANCEL.value): ExecutionState.CANCELLED.value,
    (ExecutionState.PARTIALLY_FILLED.value, ExecutionEvent.RECONCILE_FOUND_FILLED.value): ExecutionState.FILLED.value,

    # Submission Unknown Reconciliation transitions
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_FOUND_FILLED.value): ExecutionState.FILLED.value,
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_FOUND_PARTIAL.value): ExecutionState.PARTIALLY_FILLED.value,
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_FOUND_SUBMITTED.value): ExecutionState.SUBMITTED.value,
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_FOUND_CANCELLED.value): ExecutionState.CANCELLED.value,
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_ABSENT.value): ExecutionState.RECONCILE_ABSENT.value,
    (ExecutionState.SUBMISSION_UNKNOWN.value, ExecutionEvent.RECONCILE_UNCERTAIN.value): ExecutionState.SUBMISSION_UNKNOWN.value,

    # Reconciled Absent can be safely retried
    (ExecutionState.RECONCILE_ABSENT.value, ExecutionEvent.SUBMIT.value): ExecutionState.SUBMITTING.value,
    (ExecutionState.BROKER_ERROR.value, ExecutionEvent.SUBMIT.value): ExecutionState.SUBMITTING.value,
}

class ExecutionStateMachine:
    @staticmethod
    def get_next_state(current_state: str, event: str) -> str:
        curr = current_state.strip()
        ev = event.strip()
        key = (curr, ev)
        
        if key not in TRANSITION_MATRIX:
            for (c, e), target in TRANSITION_MATRIX.items():
                if c.lower() == curr.lower() and e.lower() == ev.lower():
                    return target
            raise IllegalStateTransitionError(
                f"Illegal state transition: Cannot apply event '{ev}' from current state '{curr}'."
            )
        return TRANSITION_MATRIX[key]

    @staticmethod
    def can_transition(current_state: str, event: str) -> bool:
        try:
            ExecutionStateMachine.get_next_state(current_state, event)
            return True
        except IllegalStateTransitionError:
            return False
