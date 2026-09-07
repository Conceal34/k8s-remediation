# backend/agents/pipeline.py
"""
LangGraph Multi-Agent Pipeline: wires Diagnosis -> Remediation -> Critic -> Loop Control -> Policy Engine.
"""
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
import asyncio, json, yaml
from .diagnosis_agent import run_diagnosis
from .remediation_agent import run_remediation
from .critic_agent import run_critic
from database.session import SessionLocal
from database.models import AuditLogEntry
from datetime import datetime, timezone

with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)

MAX_ROUNDS = CFG["agents"]["max_debate_rounds"]   # 2

# ── SSE broadcaster ────────────────────────────────────────────────────────────
# Any number of frontend clients can subscribe; each gets their own queue.
_sse_subscribers: list[asyncio.Queue] = []

def _broadcast(event: dict):
    """Push a JSON-serialisable event to every connected SSE client."""
    for q in list(_sse_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass

def sse_subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_subscribers.append(q)
    return q

def sse_unsubscribe(q: asyncio.Queue):
    _sse_subscribers.discard(q) if hasattr(_sse_subscribers, 'discard') else (
        _sse_subscribers.remove(q) if q in _sse_subscribers else None
    )


class PipelineState(TypedDict):
    """
    Shared mutable state object that flows through all LangGraph nodes.
    """
    # ── Input context ─────────────────────────────────────────────────────────
    anomaly_id    : int
    service       : str
    metric_type   : str
    anomaly_score : float
    severity      : str
    recent_history: list[dict]        # [{metric_type, value, timestamp, service}]

    # ── Agent outputs (accumulated across rounds) ─────────────────────────────
    diagnosis_text: Optional[str]
    proposals     : list[dict]        # [{round, action, justification, confidence, risk_tier}]
    verdicts      : list[dict]        # [{round, verdict, reason}]

    # ── Loop control ──────────────────────────────────────────────────────────
    round_num       : int             # Starts at 1, max = max_debate_rounds
    consensus_reached: Optional[bool]
    final_action    : Optional[str]
    confidence_score: Optional[float]
    risk_tier       : Optional[str]
    autonomy_outcome: Optional[str]

    # ── Error / fallback ──────────────────────────────────────────────────────
    pipeline_error  : Optional[str]


# ── Helper: write audit log ───────────────────────────────────────────────────
def _audit(ref_type: str, ref_id: int, event: str, detail: dict = None):
    db = SessionLocal()
    try:
        db.add(AuditLogEntry(
            ref_type=ref_type,
            ref_id=ref_id,
            event=event,
            detail=detail,
            timestamp=datetime.now(timezone.utc)
        ))
        db.commit()
    finally:
        db.close()


# ── Node: Diagnosis ───────────────────────────────────────────────────────────
def diagnosis_node(state: PipelineState) -> PipelineState:
    """FR-3.1"""
    try:
        text = run_diagnosis(state)
        _audit("anomaly", state["anomaly_id"], "diagnosis_complete", {"diagnosis": text})
        result = {**state, "diagnosis_text": text}
        _broadcast({"type": "diagnosis", "anomaly_id": state["anomaly_id"],
                    "service": state["service"], "text": text})
        return result
    except Exception as exc:
        _broadcast({"type": "error", "anomaly_id": state["anomaly_id"],
                    "service": state["service"], "message": str(exc)})
        return {**state, "pipeline_error": f"DiagnosisAgent failed: {exc}"}


# ── Node: Remediation ─────────────────────────────────────────────────────────
def remediation_node(state: PipelineState) -> PipelineState:
    """FR-3.2"""
    if state.get("pipeline_error"):
        return state
    try:
        feedback = state["verdicts"][-1]["reason"] if state["verdicts"] else ""
        proposal = run_remediation(state, critic_feedback=feedback)
        proposal["round"] = state["round_num"]
        _audit("anomaly", state["anomaly_id"], f"round{state['round_num']}_proposal", proposal)
        result = {**state, "proposals": state["proposals"] + [proposal]}
        _broadcast({"type": "remediation", "anomaly_id": state["anomaly_id"],
                    "service": state["service"], "proposal": proposal})
        return result
    except Exception as exc:
        return {**state, "pipeline_error": f"RemediationAgent failed: {exc}"}


# ── Node: Critic ──────────────────────────────────────────────────────────────
def critic_node(state: PipelineState) -> PipelineState:
    """FR-3.3"""
    if state.get("pipeline_error"):
        return state
    try:
        latest = state["proposals"][-1]
        verdict = run_critic(state, latest)
        verdict["round"] = state["round_num"]
        event = f"round{state['round_num']}_critic_{verdict['verdict'].lower()}"
        _audit("anomaly", state["anomaly_id"], event, verdict)
        result = {**state, "verdicts": state["verdicts"] + [verdict]}
        _broadcast({"type": "critic", "anomaly_id": state["anomaly_id"],
                    "service": state["service"], "verdict": verdict})
        return result
    except Exception as exc:
        return {**state, "pipeline_error": f"CriticAgent failed: {exc}"}


# ── Node: Loop Controller ─────────────────────────────────────────────────────
def loop_controller(state: PipelineState) -> PipelineState:
    """
    FR-3.4: Advance round or terminate.
    FR-3.5: Force no-consensus + low confidence if cap reached without APPROVE.
    """
    if state.get("pipeline_error"):
        return state

    latest_verdict = state["verdicts"][-1]["verdict"] if state["verdicts"] else "REVISE"

    if latest_verdict == "APPROVE":
        # Consensus reached
        p = state["proposals"][-1]
        return {
            **state,
            "consensus_reached": True,
            "final_action":      p["action"],
            "confidence_score":  p["confidence"],
            "risk_tier":         p["risk_tier"],
        }
    elif state["round_num"] >= MAX_ROUNDS:
        # Cap reached, force low confidence and escalation
        p = state["proposals"][-1]
        _audit("anomaly", state["anomaly_id"], "no_consensus")
        return {
            **state,
            "consensus_reached": False,
            "final_action":      p["action"],
            "confidence_score":  0.0,
            "risk_tier":         "high",
        }
    else:
        # Continue to next round
        return {**state, "round_num": state["round_num"] + 1}


# ── Conditional Edge ──────────────────────────────────────────────────────────
def _should_continue(state: PipelineState) -> Literal["remediation", "policy"]:
    """Route back to Remediation for another round, or forward to Policy Engine."""
    if state.get("pipeline_error"):
        return "policy"
    if state.get("consensus_reached") is not None:
        return "policy"
    latest_verdict = state["verdicts"][-1]["verdict"] if state["verdicts"] else "REVISE"
    if latest_verdict == "REVISE" and state["round_num"] <= MAX_ROUNDS:
        return "remediation"
    return "policy"


# ── Node: Policy Engine ───────────────────────────────────────────────────────
def policy_node(state: PipelineState) -> PipelineState:
    """FR-4.1 / FR-4.2: Route to Executor or Approval Gate."""
    from policy.autonomy_engine import route_decision
    return route_decision(state)


# ── Build & Compile Graph ─────────────────────────────────────────────────────
def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("diagnosis",    diagnosis_node)
    graph.add_node("remediation",  remediation_node)
    graph.add_node("critic",       critic_node)
    graph.add_node("loop_control", loop_controller)
    graph.add_node("policy",       policy_node)

    graph.set_entry_point("diagnosis")
    graph.add_edge("diagnosis",    "remediation")
    graph.add_edge("remediation",  "critic")
    graph.add_edge("critic",       "loop_control")
    graph.add_conditional_edges("loop_control", _should_continue)
    graph.add_edge("policy",       END)

    return graph.compile()


compiled_pipeline = build_pipeline()


async def handle_anomaly(anomaly, context: list) -> dict:
    from database.session import SessionLocal
    from database.models import Anomaly
    from sqlalchemy.orm import joinedload
    db = SessionLocal()
    anomaly = db.query(Anomaly).options(joinedload(Anomaly.metric_sample)).filter_by(id=anomaly.id).first()
    db.close()

    history = [
        {
            "timestamp":   str(s.timestamp),
            "service":     s.service,
            "metric_type": s.metric_type,
            "value":       float(s.value),
        }
        for s in context if s.service == anomaly.metric_sample.service
    ]

    initial: PipelineState = {
        "anomaly_id":       anomaly.id,
        "service":          anomaly.metric_sample.service,
        "metric_type":      anomaly.metric_sample.metric_type,
        "anomaly_score":    float(anomaly.score),
        "severity":         anomaly.severity,
        "recent_history":   history,
        "diagnosis_text":   None,
        "proposals":        [],
        "verdicts":         [],
        "round_num":        1,
        "consensus_reached": None,
        "final_action":     None,
        "confidence_score": None,
        "risk_tier":        None,
        "autonomy_outcome": None,
        "pipeline_error":   None,
    }

    print(f"[Pipeline] Starting for anomaly {anomaly.id} | service={initial['service']} severity={initial['severity']}")
    _broadcast({
        "type":       "anomaly_detected",
        "anomaly_id": anomaly.id,
        "service":    anomaly.metric_sample.service,
        "severity":   anomaly.severity,
        "score":      float(anomaly.score),
        "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None,
    })
    final_state = await compiled_pipeline.ainvoke(initial)
    _broadcast({
        "type":    "outcome",
        "anomaly_id": anomaly.id,
        "service": final_state.get("service"),
        "outcome": final_state.get("autonomy_outcome"),
        "action":  final_state.get("final_action"),
        "confidence": final_state.get("confidence_score"),
    })
    print(f"[Pipeline] Done for anomaly {anomaly.id} | outcome={final_state.get('autonomy_outcome', 'unknown')}")
    return final_state
