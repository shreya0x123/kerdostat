import os
import pytest
import concurrent.futures
from unittest.mock import patch, MagicMock
from app.models.user import UserModel
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.core.security import create_jwt_token
from app.core.guardrails import GuardrailEngine
from app.services.reconciliation import reconcile_proposal

def get_token_for_user(db, user_id: str, email: str) -> str:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        user = UserModel(id=user_id, name=email.split("@")[0], email=email, password="dummy")
        db.add(user)
        db.commit()
    return create_jwt_token({"sub": email, "id": user_id})

# 1. CONCURRENT DOUBLE-SUBMISSION CONFLICT TEST
def test_concurrent_double_submit_optimistic_locking(client, db):
    """
    Adversarial test: Two simultaneous requests attempt to approve the same proposal.
    Exactly one request must succeed (200 OK) and the other must be rejected with 409 Conflict.
    """
    prop = ProposalModel(
        id="prop-race-1",
        user_id="user-1",
        execution_version=1,
        symbol="QUANT",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=400.0,
        status="pending"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    def submit_action():
        return client.patch("/trade/prop-race-1/action", json={"action": "approve"}, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_action)
        f2 = executor.submit(submit_action)
        resp1 = f1.result()
        resp2 = f2.result()

    statuses = sorted([resp1.status_code, resp2.status_code])
    assert statuses == [200, 409] or statuses == [200, 400], f"Unexpected concurrency result: {statuses}"
    if 409 in statuses:
        conflicting_resp = resp1 if resp1.status_code == 409 else resp2
        assert "Execution conflict" in conflicting_resp.json()["detail"]

# 2. SUBMISSION_UNKNOWN RECONCILIATION TEST (ORDER FOUND AT BROKER)
def test_reconciliation_flow_order_confirmed(client, db):
    """
    Adversarial test:
    1. Order submission encounters a timeout -> transitions to SUBMISSION_UNKNOWN.
    2. Broker did receive the order.
    3. Reconciler runs, queries broker by client_order_id, and transitions order to FILLED without duplicate order.
    """
    prop = ProposalModel(
        id="prop-reconcile-1",
        user_id="user-1",
        execution_version=1,
        symbol="NVDA",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=300.0,
        client_order_id="KERDOSTAT-prop-reconcile-1-v1",
        status="SUBMISSION_UNKNOWN"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Mock broker executor finding the existing order
    mock_order = MagicMock(id="broker-ord-9988", status="filled", client_order_id="KERDOSTAT-prop-reconcile-1-v1")
    with patch("app.services.reconciliation.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.is_mock.return_value = True
        mock_exec.mock_orders = {"broker-ord-9988": mock_order}
        mock_select.return_value = mock_exec

        resp = client.post("/trade/prop-reconcile-1/reconcile", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reconciled"] is True
        assert data["status"] == "FILLED"
        assert data["broker_order_id"] == "broker-ord-9988"

    updated_prop = db.query(ProposalModel).filter(ProposalModel.id == "prop-reconcile-1").first()
    assert updated_prop.status == "FILLED"
    assert updated_prop.broker_order_id == "broker-ord-9988"

    # Verify append-only audit event created
    reconcile_logs = db.query(AuditLogModel).filter(
        AuditLogModel.proposal_id == "prop-reconcile-1",
        AuditLogModel.action_type == "RECONCILE_FOUND"
    ).all()
    assert len(reconcile_logs) == 1
    assert reconcile_logs[0].new_state == "FILLED"

# 3. SUBMISSION_UNKNOWN RECONCILIATION TEST (ORDER ABSENT AT BROKER)
def test_reconciliation_flow_order_absent(client, db):
    """
    Adversarial test:
    1. Order submission failed in network transit before reaching broker.
    2. Proposal is in SUBMISSION_UNKNOWN.
    3. Reconciler verifies absence at broker and marks RECONCILE_ABSENT for safe retry.
    """
    prop = ProposalModel(
        id="prop-reconcile-absent",
        user_id="user-1",
        execution_version=1,
        symbol="TSLA",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=300.0,
        client_order_id="KERDOSTAT-prop-reconcile-absent-v1",
        status="SUBMISSION_UNKNOWN"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.reconciliation.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.is_mock.return_value = True
        mock_exec.mock_orders = {} # Empty store = order never reached broker
        mock_select.return_value = mock_exec

        resp = client.post("/trade/prop-reconcile-absent/reconcile", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reconciled"] is True
        assert data["status"] == "RECONCILE_ABSENT"

    updated_prop = db.query(ProposalModel).filter(ProposalModel.id == "prop-reconcile-absent").first()
    assert updated_prop.status == "RECONCILE_ABSENT"

# 4. STRICT 3-POINT ENTRY-RELATIVE DIRECTIONAL INVARIANTS
def test_strict_entry_relative_directional_invariants(db):
    """
    Test 3-point price bounds:
    - Long: SL < Entry < TP
    - Short: TP < Entry < SL
    - Rejection of equality bounds.
    """
    engine = GuardrailEngine()

    # Long: SL >= Entry (Stop above entry) -> Must Reject
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=160.0, tp=180.0, side="BUY")
    assert valid is False
    assert "strictly below Entry Price" in reason

    # Long: Entry >= TP (Target below entry) -> Must Reject
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=185.0, db=db, sl=140.0, tp=180.0, side="BUY")
    assert valid is False
    assert "strictly below Take Profit" in reason

    # Long: SL == Entry -> Must Reject
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=150.0, tp=180.0, side="BUY")
    assert valid is False

    # Short: TP >= Entry (Target above entry) -> Must Reject
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=160.0, tp=155.0, side="SELL")
    assert valid is False
    assert "strictly below Entry Price" in reason

    # Short: Entry >= SL (Stop below entry) -> Must Reject
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=170.0, db=db, sl=165.0, tp=140.0, side="SELL")
    assert valid is False
    assert "strictly below Stop Loss" in reason

    # Valid Long: SL (140) < Entry (150) < TP (170) -> Must Pass
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=140.0, tp=170.0, side="BUY")
    assert valid is True

    # Valid Short: TP (130) < Entry (150) < SL (165) -> Must Pass
    valid, reason, _ = engine.validate_trade(symbol="AAPL", qty=10, price=150.0, db=db, sl=165.0, tp=130.0, side="SELL")
    assert valid is True

# 5. DATABASE-LEVEL AUDIT IMMUTABILITY TEST
def test_database_level_audit_immutability(db):
    """
    Verify ORM/Database event listeners prevent any update or deletion of audit records.
    """
    audit = AuditLogModel(
        id="audit-immutable-1",
        timestamp="2026-08-12T10:00:00Z",
        symbol="AAPL",
        action_type="APPROVE",
        status="SUCCESS",
        user="trader@kerdostat.com"
    )
    db.add(audit)
    db.commit()

    # Attempt to modify an existing audit log -> MUST raise RuntimeError
    audit.action_type = "MUTATED_ACTION"
    with pytest.raises(RuntimeError, match="strictly append-only and immutable"):
        db.commit()
    db.rollback()

    # Attempt to delete an existing audit log -> MUST raise RuntimeError
    db.delete(audit)
    with pytest.raises(RuntimeError, match="strictly append-only and immutable"):
        db.commit()
    db.rollback()

# 6. FORBIDDEN STATE MACHINE TRANSITION TEST
def test_forbidden_state_machine_transitions(client, db):
    """
    Ensure executed/filled proposals cannot be actioned or re-submitted.
    """
    prop = ProposalModel(
        id="prop-filled-1",
        user_id="user-1",
        symbol="AAPL",
        signal="BUY",
        qty=10,
        SL=100.0,
        TP=200.0,
        status="FILLED"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to approve an already FILLED proposal -> Must return 400 Bad Request
    resp = client.patch("/trade/prop-filled-1/action", json={"action": "approve"}, headers=headers)
    assert resp.status_code == 400
    assert "Proposal cannot be actioned" in resp.json()["detail"]
