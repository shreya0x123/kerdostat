from sqlalchemy import Column, String, Integer, Float
from app.core.database import Base

class ProposalModel(Base):
    __tablename__ = "proposals"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, default="user-1", index=True)
    execution_version = Column(Integer, nullable=False, default=1)
    symbol = Column(String, nullable=False)
    signal = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    SL = Column(Float, nullable=False)
    TP = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="pending")
    XAIReason = Column(String, nullable=True)
    risk_score = Column(Float, default=3.0)
    
    # Partial-Fill & Execution Telemetry
    requested_qty = Column(Integer, nullable=True)
    filled_qty = Column(Integer, nullable=False, default=0)
    remaining_qty = Column(Integer, nullable=True)
    avg_fill_price = Column(Float, nullable=True)
    last_broker_update = Column(String, nullable=True)

    # Provenance & Check-Time Snapshot Telemetry
    data_source = Column(String, nullable=False, default="LIVE")
    data_timestamp = Column(String, nullable=True)
    equity_at_check = Column(Float, nullable=True)
    buying_power_at_check = Column(Float, nullable=True)
    cash_at_check = Column(Float, nullable=True)
    risk_limit_at_check = Column(Float, nullable=True)
    
    # Execution-Time Snapshot Telemetry
    equity_at_execution = Column(Float, nullable=True)
    buying_power_at_execution = Column(Float, nullable=True)
    cash_at_execution = Column(Float, nullable=True)
    
    # Deterministic Idempotency, Broker routing & Reconciliation Telemetry
    client_order_id = Column(String, nullable=True)
    broker_order_id = Column(String, nullable=True)
    reconcile_attempts = Column(Integer, nullable=False, default=0)
    last_reconciled_at = Column(String, nullable=True)
