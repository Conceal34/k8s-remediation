from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from database.session import get_db
from database.models  import Decision, Anomaly, Approval
from cache            import cache_get, cache_set, cache_invalidate, KEYS, TTL

router = APIRouter()

def _serialize_decision(d: Decision) -> dict:
    service = "payment-service"
    anomaly_data = None
    if d.anomaly:
        if d.anomaly.metric_sample:
            service = d.anomaly.metric_sample.service
        anomaly_data = {
            "id": d.anomaly.id,
            "metric_sample_id": d.anomaly.metric_sample_id,
            "score": float(d.anomaly.score),
            "severity": d.anomaly.severity,
            "detected_at": d.anomaly.detected_at.isoformat() if d.anomaly.detected_at else None,
            "service": service,
        }

    return {
        "id": d.id,
        "anomaly_id": d.anomaly_id,
        "service": service,
        "diagnosis_text": d.diagnosis_text,
        "remediation_proposals": d.remediation_proposals,
        "critic_verdicts": d.critic_verdicts,
        "round_count": d.round_count,
        "consensus_reached": d.consensus_reached,
        "final_action": d.final_action,
        "risk_tier": d.risk_tier,
        "confidence_score": float(d.confidence_score) if d.confidence_score is not None else 0.0,
        "autonomy_outcome": d.autonomy_outcome,
        "pipeline_error": d.pipeline_error,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "anomaly": anomaly_data,
        "approval": {
            "id": d.approval.id,
            "operator": d.approval.operator,
            "action_taken": d.approval.action_taken,
            "edited_action": d.approval.override_action,
            "acted_at": d.approval.decided_at.isoformat() if d.approval.decided_at else None,
        } if d.approval else None,
    }


@router.get("/")
def list_decisions(
    db: Session = Depends(get_db),
    risk:    str | None = Query(None),
    outcome: str | None = Query(None),
    limit:   int = Query(50, le=500),
):
    """FR-6.2: Filterable full decision history. Redis-cached for 6s (no cache for filters)."""
    # Only cache the unfiltered default query
    if not risk and not outcome and limit == 50:
        cached = cache_get(KEYS["decisions_list"])
        if cached is not None:
            return cached

    q = db.query(Decision).options(
        joinedload(Decision.anomaly).joinedload(Anomaly.metric_sample),
        joinedload(Decision.approval)
    )
    if risk:    q = q.filter(Decision.risk_tier == risk)
    if outcome: q = q.filter(Decision.autonomy_outcome == outcome)
    decisions = q.order_by(Decision.created_at.desc()).limit(limit).all()
    result = [_serialize_decision(d) for d in decisions]

    if not risk and not outcome and limit == 50:
        cache_set(KEYS["decisions_list"], result, TTL["decisions_list"])
    return result


@router.get("/escalated")
def list_escalated(db: Session = Depends(get_db)):
    """FR-6.1: Return all escalated decisions. Redis-cached for 6s."""
    cached = cache_get(KEYS["decisions_escalated"])
    if cached is not None:
        return cached

    decisions = (
        db.query(Decision)
          .options(
              joinedload(Decision.anomaly).joinedload(Anomaly.metric_sample),
              joinedload(Decision.approval)
          )
          .filter(Decision.autonomy_outcome == "escalated")
          .filter(~Decision.approval.has())
          .order_by(Decision.created_at.desc())
          .all()
    )
    result = [_serialize_decision(d) for d in decisions]
    cache_set(KEYS["decisions_escalated"], result, TTL["decisions_escalated"])
    return result


@router.get("/{decision_id}")
def get_decision(decision_id: int, db: Session = Depends(get_db)):
    """FR-6.3: Full detail for a specific decision. Not cached (individual ID)."""
    d = (
        db.query(Decision)
          .options(
              joinedload(Decision.anomaly).joinedload(Anomaly.metric_sample),
              joinedload(Decision.approval)
          )
          .filter(Decision.id == decision_id)
          .first()
    )
    return _serialize_decision(d) if d else None


@router.delete("/cache")
def bust_decision_cache():
    """Admin endpoint: manually bust all decision-related caches."""
    cache_invalidate(KEYS["decisions_list"], KEYS["decisions_escalated"])
    return {"status": "cache invalidated"}
