from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="trader")
    mode = Column(String, default="COPILOT")  # COPILOT (HITL) or AUTOPILOT (HOTL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradeProposal(Base):
    __tablename__ = "trade_proposals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)  # 0-10
    indicator_summary = Column(Text)
    status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    trade_proposal_id = Column(Integer, ForeignKey("trade_proposals.id"))
    action_taken = Column(String, nullable=False)
    decision_by = Column(String, nullable=False)
    reason = Column(Text)
    mode = Column(String, default="HITL")
    override_delta = Column(Float, nullable=True)
    guardrail_hit = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())