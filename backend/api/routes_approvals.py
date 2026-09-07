from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from approval.approval_gate import process_operator_decision

router = APIRouter()

class ApprovalRequest(BaseModel):
    operator:      str
    action_taken:  str              # approve | edit | reject
    edited_action: str | None = None

@router.post("/{decision_id}")
def submit_approval(decision_id: int, body: ApprovalRequest):
    """FR-4.3: Operator submits approve / edit / reject for an escalated decision."""
    if body.action_taken not in ("approve", "edit", "reject"):
        raise HTTPException(status_code=400, detail="action_taken must be approve | edit | reject")
    if body.action_taken == "edit" and not body.edited_action:
        raise HTTPException(status_code=400, detail="edited_action required when action_taken=edit")
    return process_operator_decision(
        decision_id   = decision_id,
        operator      = body.operator,
        action_taken  = body.action_taken,
        edited_action = body.edited_action,
    )
