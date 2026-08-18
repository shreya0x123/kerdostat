import pytest
from unittest.mock import patch, MagicMock
from app.models.user import UserModel
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.core.security import create_jwt_token

def get_token_for_user(db, user_id: str, email: str) -> str:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        user = UserModel(id=user_id, name=email.split("@")[0], email=email, password="dummy")
        db.add(user)
        db.commit()
    return create_jwt_token({"sub": email, "id": user_id})

def test_idor_proposal_ownership_protection(client, db):
    """Ensure User B cannot approve or modify User A's proposal."""
    user_a = UserModel(id="user-alpha", name="Alpha User", email="alpha@kerdostat.com", password="hash")
    user_b = UserModel(id="user-bravo", name="Bravo User", email="bravo@kerdostat.com", password="hash")
    db.add(user_a)
    db.add(user_b)
    db.commit()

    prop_a = ProposalModel(
        id="prop-alpha-101",
        user_id="user-alpha",
        symbol="AAPL",
        signal="BUY",
        qty=10,
        SL=150.0,
        TP=200.0,
        status="pending"
    )
    db.add(prop_a)
    db.commit()

    token_b = get_token_for_user(db, "user-bravo", "bravo@kerdostat.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    resp = client.patch("/trade/prop-alpha-101/action", json={"action": "approve"}, headers=headers_b)
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]

def test_deterministic_idempotency_key(client, db):
    """Ensure client_order_id is deterministically derived from proposal ID and version."""
    prop = ProposalModel(
        id="prop-idemp-1",
        user_id="user-1",
        execution_version=2,
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

    with patch("app.routers.trade.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_order = MagicMock(id="order-mock-idemp-1")
        mock_exec.submit_order.return_value = mock_order
        mock_select.return_value = mock_exec

        resp = client.patch("/trade/prop-idemp-1/action", json={"action": "approve"}, headers=headers)
        assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
        assert resp.json()["client_order_id"] == "KERDOSTAT-prop-idemp-1-v2"

def test_wrong_side_stop_loss_rejection(client, db):
    """Reject BUY proposals where Stop-Loss is above target."""
    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    prop = ProposalModel(
        id="prop-wrong-sl",
        user_id="user-1",
        symbol="AAPL",
        signal="BUY",
        qty=10,
        SL=250.0, # Wrong side (above TP)
        TP=200.0,
        status="pending"
    )
    db.add(prop)
    db.commit()

    resp = client.patch("/trade/prop-wrong-sl/action", json={"action": "approve"}, headers=headers)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]

def test_broker_timeout_state_transition(client, db):
    """Verify network timeouts transition order to SUBMISSION_UNKNOWN rather than swallowing."""
    prop = ProposalModel(
        id="prop-timeout-1",
        user_id="user-1",
        symbol="NVDA",
        signal="BUY",
        qty=5,
        SL=100.0,
        TP=200.0,
        status="pending"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.routers.trade.select_executor_by_symbol") as mock_select:
        mock_exec = MagicMock()
        mock_exec.submit_order.side_effect = Exception("HTTPSConnectionPool timeout connecting to broker")
        mock_select.return_value = mock_exec

        resp = client.patch("/trade/prop-timeout-1/action", json={"action": "approve"}, headers=headers)
        assert resp.status_code == 502

    updated_prop = db.query(ProposalModel).filter(ProposalModel.id == "prop-timeout-1").first()
    assert updated_prop.status == "SUBMISSION_UNKNOWN"

def test_account_snapshot_persistence(client, db):
    """Verify decision-time equity and buying power are recorded on the proposal."""
    prop = ProposalModel(
        id="prop-snapshot-1",
        user_id="user-1",
        symbol="TSLA",
        signal="BUY",
        qty=5,
        SL=100.0,
        TP=300.0,
        status="pending"
    )
    db.add(prop)
    db.commit()

    token = get_token_for_user(db, "user-1", "trader@kerdostat.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.patch("/trade/prop-snapshot-1/action", json={"action": "approve"}, headers=headers)
    assert resp.status_code == 200

    updated_prop = db.query(ProposalModel).filter(ProposalModel.id == "prop-snapshot-1").first()
    assert updated_prop.buying_power_at_check is not None
    assert updated_prop.equity_at_check is not None
