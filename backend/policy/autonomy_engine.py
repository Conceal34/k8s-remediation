# backend/policy/autonomy_engine.py
"""
Autonomy Policy Engine — FR-4.1, FR-4.2, FR-4.3, FR-4.4
Reads risk tier + confidence + consensus; routes to Executor or Approval Gate.
"""
import yaml
from database.session import SessionLocal
from database.models  import Decision, AuditLogEntry
from datetime         import datetime, timezone

with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)

CONFIDENCE_THRESHOLD = CFG["policy"]["confidence_threshold"]   # 0.80


def route_decision(state: dict) -> dict:
    """
    FR-4.1: Auto-execute if risk=low AND confidence>=threshold AND consensus=True
    FR-4.2: Escalate in all other cases (incl. pipeline errors, FR-3.6)
    """
    # FR-3.6: Pipeline error → always escalate safely
    if state.get("pipeline_error"):
        state.update({
            "final_action":     "escalate_no_op",
            "risk_tier":        "high",
            "confidence_score": 0.0,
            "consensus_reached": False,
            "autonomy_outcome": "escalated",
        })
        print(f"[PolicyEngine] Pipeline error -> escalating: {state['pipeline_error']}")
        _persist_and_route(state, outcome="escalated")
        return state

    risk       = state.get("risk_tier",        "high")
    confidence = state.get("confidence_score",  0.0)
    consensus  = state.get("consensus_reached", False)

    should_auto_execute = (
        risk == "low" and
        confidence >= CONFIDENCE_THRESHOLD and
        consensus is True
    )

    if should_auto_execute:
        state["autonomy_outcome"] = "auto_executed"
        print(f"[PolicyEngine] AUTO-EXECUTE: {state['final_action']} (conf={confidence:.2f})")
        _persist_and_route(state, outcome="auto_executed")
    else:
        reason = _escalation_reason(risk, confidence, consensus)
        state["autonomy_outcome"] = "escalated"
        print(f"[PolicyEngine] ESCALATE: {reason}")
        _persist_and_route(state, outcome="escalated")

    return state


def _escalation_reason(risk: str, confidence: float, consensus: bool) -> str:
    parts = []
    if risk == "high":                          parts.append("risk_tier=high")
    if confidence < CONFIDENCE_THRESHOLD:       parts.append(f"confidence={confidence:.2f}<{CONFIDENCE_THRESHOLD}")
    if not consensus:                           parts.append("no_consensus")
    return ", ".join(parts) or "unknown"


def _persist_and_route(state: dict, outcome: str):
    """Write Decision row to DB, write audit log, then call Executor or Approval Gate."""
    db = SessionLocal()
    try:
        decision = Decision(
            anomaly_id            = state["anomaly_id"],
            diagnosis_text        = state.get("diagnosis_text") or "Pipeline error - no diagnosis.",
            remediation_proposals = state.get("proposals", []),
            critic_verdicts       = state.get("verdicts",  []),
            round_count           = state.get("round_num",  1),
            consensus_reached     = state.get("consensus_reached", False),
            final_action          = state.get("final_action", "escalate_no_op"),
            risk_tier             = state.get("risk_tier",    "high"),
            confidence_score      = state.get("confidence_score", 0.0),
            autonomy_outcome      = outcome,
            pipeline_error        = state.get("pipeline_error"),
            created_at            = datetime.now(timezone.utc),
        )
        db.add(decision)
        db.flush()

        db.add(AuditLogEntry(
            ref_type="decision",
            ref_id=decision.id,
            event=outcome,
            detail={"final_action": decision.final_action, "risk_tier": decision.risk_tier, "confidence": float(decision.confidence_score)},
            timestamp=datetime.now(timezone.utc)
        ))
        db.commit()
        state["decision_id"] = decision.id
        # Immediately bust cached decisions so the dashboard shows the new one
        try:
            from cache import invalidate_decision_caches
            invalidate_decision_caches()
        except Exception:
            pass
    finally:
        db.close()

    # Route to the appropriate downstream module
    try:
        if outcome == "auto_executed":
            from executor.k8s_executor import execute_action
            execute_action(state)
        else:
            from approval.approval_gate import hold_for_operator
            hold_for_operator(state)
    except Exception as exc:
        print(f"[PolicyEngine] Downstream routing notice: {exc}")
