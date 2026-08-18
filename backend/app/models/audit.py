import uuid
from sqlalchemy import Column, String, Integer, Float, event
from app.core.database import Base

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, nullable=True, index=True)
    proposal_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    
    # Audit telemetry & correlation
    correlation_id = Column(String, nullable=True, index=True)
    request_id = Column(String, nullable=True)
    execution_version = Column(Integer, nullable=True)
    strategy_id = Column(String, nullable=True, default="BREAKOUT_XAI_V1")
    model_version = Column(String, nullable=True, default="xai-rules-v2.1")
    actor_type = Column(String, nullable=True, default="USER")
    
    # Precise timestamps
    timestamp = Column(String, nullable=False)
    event_timestamp = Column(String, nullable=True)
    data_timestamp = Column(String, nullable=True)
    
    # Financial state
    symbol = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    event_type = Column(String, nullable=True)
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=True)
    qty = Column(Integer, nullable=False, default=0)
    price = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False)
    user = Column(String, nullable=False)
    
    # Provenance and tracking
    client_order_id = Column(String, nullable=True)
    broker_order_id = Column(String, nullable=True)
    data_source = Column(String, nullable=True, default="LIVE")
    reason = Column(String, nullable=True)

# Enforce Append-Only Immutability below application code
@event.listens_for(AuditLogModel, "before_update")
def receive_before_update(mapper, connection, target):
    raise RuntimeError("AuditLogModel is strictly append-only and immutable. UPDATE operations are forbidden.")

@event.listens_for(AuditLogModel, "before_delete")
def receive_before_delete(mapper, connection, target):
    raise RuntimeError("AuditLogModel is strictly append-only and immutable. DELETE operations are forbidden.")
