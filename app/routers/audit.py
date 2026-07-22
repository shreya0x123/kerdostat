"""
app/routers/audit.py
GET /audit/log — paginated audit trail
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import AuditLog, User
from app.schemas.schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/log",
    response_model=List[AuditLogResponse],
    summary="Get paginated audit trail",
    description="""
## Audit Trail
Returns a paginated, immutable audit log of every decision made in the system.

**Every entry records:**
- Who made the decision (username)
- What action was taken (COMMIT, REJECT, MODIFY, OVERRIDE, EXECUTED, GUARDRAIL_BLOCKED)
- Exact timestamp
- Reason for the decision
- Mode (HITL or HOTL)
- Guardrail hit details if blocked

**Query parameters:**
- `page` — page number (default 1)
- `page_size` — results per page (default 10)

**Responses:**
- `200` — List of audit entries ordered by newest first
- `401` — Invalid or expired token

**Requires JWT authentication.**
    """
)
def get_audit_log(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * page_size
    logs = db.query(AuditLog).order_by(
        AuditLog.timestamp.desc()
    ).offset(offset).limit(page_size).all()
    return logs
