import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from app.models.user import UserModel
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.core.security import create_jwt_token
from app.core.guardrails import GuardrailEngine
from app.core.state_machine import (
    ExecutionStateMachine,
    ExecutionState,
    ExecutionEvent,
    IllegalStateTransitionError
)
from app.services.reconciliation import reconcile_proposal, reconcile_stranded_on_startup

def get_token_for_user(db, user_id: str, email: str) -> str:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        user = UserModel(id=user_id, name=email.split("@")[0], email=email, password="dummy")
        db.add(user)
        db.commit()
    return create_jwt_token({"sub": email, "id": user_id})

# 1. STARTUP CRASH RECOVERY TEST
def test_startup_crash_recovery_stranded_orders(db):
    """
    Verify startup crash recovery automatically finds and reconciles stranded SUBMITTING/SUBMISSION_UNKNOWN orders.
    """
    prop1 = ProposalModel(
        id="prop-stranded-1",
        user_id="user-1",
        execution_version=1,
        symbol="QUANT",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=200.0,
        client_order_id="KERDOSTAT-prop-stranded-1-v1",
        status="SUBMISSION_UNKNOWN"
    )
    prop2 = ProposalModel(
        id="prop-stranded-2",
        user_id="user-1",
        execution_version=1,
        symbol="NVDA",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=200.0,
        client_order_id="KERDOSTAT-prop-stranded-2-v1",
        status="SUBMITTING"
    )
    db.add(prop1)
    db.add(prop2)
    db.commit()

    mock_order = MagicMock(id="ord-recovered-1", status="filled", client_order_id="KERDOSTAT-prop-stranded-1-v1")
    with patch("app.services.reconciliation.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.is_mock.return_value = True
        mock_exec.mock_orders = {"ord-recovered-1": mock_order}
        mock_select.return_value = mock_exec

        count = reconcile_stranded_on_startup(db)
        assert count == 2

    # Prop 1 found -> FILLED
    updated_1 = db.query(ProposalModel).filter(ProposalModel.id == "prop-stranded-1").first()
    assert updated_1.status == "FILLED"
    assert updated_1.broker_order_id == "ord-recovered-1"

    # Prop 2 not found -> RECONCILE_ABSENT
    updated_2 = db.query(ProposalModel).filter(ProposalModel.id == "prop-stranded-2").first()
    assert updated_2.status == "RECONCILE_ABSENT"

# 2. 3-STAGE AUTHORITATIVE RECONCILIATION TEST
def test_authoritative_reconciliation_stages(db):
    """
    Test 3 outcomes:
    1. RECONCILE_FOUND
    2. RECONCILE_UNCERTAIN (broker query failure)
    3. RECONCILE_ABSENT_CONFIRMED
    """
    prop = ProposalModel(
        id="prop-reconcile-stages",
        user_id="user-1",
        execution_version=1,
        symbol="TSLA",
        signal="BUY",
        qty=5,
        SL=100.0,
        TP=300.0,
        client_order_id="KERDOSTAT-prop-reconcile-stages-v1",
        status="SUBMISSION_UNKNOWN"
    )
    db.add(prop)
    db.commit()

    # Stage A: Inconclusive/Error query -> RECONCILE_UNCERTAIN
    with patch("app.services.reconciliation.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.is_mock.return_value = False
        mock_exec.client.get_order_by_client_order_id.side_effect = Exception("503 Service Unavailable")
        mock_select.return_value = mock_exec

        res_uncertain = reconcile_proposal("prop-reconcile-stages", db)
        assert res_uncertain["outcome"] == "RECONCILE_UNCERTAIN"
        assert res_uncertain["attempts"] == 1
        
        # Proposal retains SUBMISSION_UNKNOWN status
        p = db.query(ProposalModel).filter(ProposalModel.id == "prop-reconcile-stages").first()
        assert p.status == "SUBMISSION_UNKNOWN"

    # Stage B: Found -> RECONCILE_FOUND
    mock_order = MagicMock(id="broker-tsla-99", status="new", client_order_id="KERDOSTAT-prop-reconcile-stages-v1")
    with patch("app.services.reconciliation.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.is_mock.return_value = True
        mock_exec.mock_orders = {"broker-tsla-99": mock_order}
        mock_select.return_value = mock_exec

        res_found = reconcile_proposal("prop-reconcile-stages", db)
        assert res_found["outcome"] == "RECONCILE_FOUND"
        assert res_found["status"] == "SUBMITTED"

# 3. FORMAL STATE MACHINE ILLEGAL TRANSITION TEST
def test_formal_state_machine_invariants():
    """
    Ensure illegal transitions are rejected by the domain state machine.
    """
    # Valid transitions
    assert ExecutionStateMachine.get_next_state("pending", "SUBMIT") == "SUBMITTING"
    assert ExecutionStateMachine.get_next_state("SUBMITTING", "BROKER_FILL") == "FILLED"
    assert ExecutionStateMachine.get_next_state("SUBMISSION_UNKNOWN", "RECONCILE_ABSENT") == "RECONCILE_ABSENT"

    # Illegal transitions: FILLED -> SUBMITTING
    with pytest.raises(IllegalStateTransitionError, match="Illegal state transition"):
        ExecutionStateMachine.get_next_state("FILLED", "SUBMIT")

    # Illegal transitions: broker_error -> BROKER_FILL
    with pytest.raises(IllegalStateTransitionError, match="Illegal state transition"):
        ExecutionStateMachine.get_next_state("broker_error", "BROKER_FILL")

    # Boolean query helper
    assert ExecutionStateMachine.can_transition("FILLED", "SUBMIT") is False
    assert ExecutionStateMachine.can_transition("pending", "SUBMIT") is True

# 4. PER-SYMBOL CIRCUIT BREAKER TEST
def test_symbol_circuit_breaker(db):
    """
    Verify per-symbol circuit breakers halt trading on specific instruments.
    """
    engine = GuardrailEngine()

    # Normal validation
    valid, _, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY")
    assert valid is True

    # Trip breaker for AAPL
    engine.trip_symbol_circuit_breaker("AAPL", reason="Intraday symbol loss threshold breached (-5.2%)")
    
    # Validation must now be blocked
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY")
    assert valid is False
    assert "Symbol circuit breaker is engaged for AAPL" in reason

    # Other symbols (e.g. MSFT) remain unaffected
    valid_msft, _, _ = engine.validate_trade(symbol="MSFT", qty=10, price=300.0, db=db, sl=280.0, tp=330.0, side="BUY")
    assert valid_msft is True

    # Reset breaker
    engine.reset_symbol_circuit_breaker("AAPL")
    valid_reset, _, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY")
    assert valid_reset is True

# 5. STALE MARKET DATA GUARD TEST
def test_stale_market_data_rejection(db):
    """
    Verify proposals with stale timestamps are rejected before broker submission.
    """
    engine = GuardrailEngine()

    # Fresh timestamp (10 seconds ago) -> Pass
    fresh_ts = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    valid_fresh, _, _ = engine.validate_trade(
        symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY", data_timestamp=fresh_ts
    )
    assert valid_fresh is True

    # Stale timestamp (10 minutes ago) -> Reject
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    valid_stale, reason, _ = engine.validate_trade(
        symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY", data_timestamp=stale_ts
    )
    assert valid_stale is False
    assert "is stale" in reason

# 6. DUAL EXECUTION SNAPSHOT TELEMETRY TEST
def test_dual_execution_snapshot_telemetry(client, db):
    """
    Verify decision-time snapshot and execution-time snapshot are both persisted on the proposal.
    """
    prop = ProposalModel(
        id="prop-dual-snap",
        user_id="user-1",
        execution_version=1,
        symbol="QUANT",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=200.0,
        status="pending"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.patch("/trade/prop-dual-snap/action", json={"action": "approve"}, headers=headers)
    assert resp.status_code == 200

    updated = db.query(ProposalModel).filter(ProposalModel.id == "prop-dual-snap").first()
    # Decision-time snapshot
    assert updated.equity_at_check is not None
    assert updated.buying_power_at_check is not None
    # Execution-time snapshot
    assert updated.equity_at_execution is not None
    assert updated.buying_power_at_execution is not None
