# backend/approval/approval_gate.py
"""
Approval Gate — FR-4.2, FR-4.3
Holds escalated decisions; processes operator approve/edit/reject from dashboard.
"""
from database.session import SessionLocal
from database.models  import Approval, AuditLogEntry, Decision
from executor.k8s_executor import execute_action
from datetime import datetime, timezone


def hold_for_operator(state: dict):
    """
    Called by Policy Engine for escalated decisions.
    Decision is already persisted in DB; the dashboard will poll /api/decisions/escalated.
    """
    print(f"[ApprovalGate] Decision {state.get('decision_id')} is held for operator review.")


def process_operator_decision(
    decision_id:   int,
    operator:      str,
    action_taken:  str,              # "approve" | "edit" | "reject"
    edited_action: str | None = None # Only if action_taken == "edit"
) -> dict:
    """
    FR-4.3: Called by REST API when operator submits their decision.
    Returns a result dict for the API response.
    """
    db = SessionLocal()
    try:
        decision = db.query(Decision).filter(Decision.id == decision_id).first()
        if not decision:
            return {"error": f"Decision {decision_id} not found"}
        if action_taken not in ("approve", "edit", "reject"):
            return {"error": f"Invalid action_taken: {action_taken}"}

        # Record operator decision
        approval = Approval(
            decision_id     = decision_id,
            operator        = operator,
            action_taken    = action_taken,
            override_action = edited_action if action_taken == "edit" else None,
            decided_at      = datetime.now(timezone.utc),
        )
        db.add(approval)
        db.add(AuditLogEntry(
            ref_type  = "decision",
            ref_id    = decision_id,
            event     = f"operator_{action_taken}",
            detail    = {"operator": operator, "action_taken": action_taken, "override_action": edited_action},
            timestamp = datetime.now(timezone.utc),
        ))
        db.commit()

        # Build execution state for the Executor
        exec_state = {
            "decision_id":  decision_id,
            "service":      decision.anomaly.metric_sample.service if decision.anomaly and decision.anomaly.metric_sample else "payment-service",
            "final_action": edited_action if action_taken == "edit" else decision.final_action,
        }

        if action_taken in ("approve", "edit"):
            execute_action(exec_state)
            
            # Fix cache mismatch: bust the cache so the UI updates immediately
            try:
                from cache import invalidate_decision_caches
                invalidate_decision_caches()
            except ImportError:
                pass
                
            return {
                "status":  "executed",
                "action":  exec_state["final_action"],
                "service": exec_state["service"],
            }
        else:  # reject
            return {"status": "rejected", "decision_id": decision_id}

    finally:
        db.close()
