from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from database.session import get_db
from database.models  import MetricSample, Anomaly
from datetime         import datetime, timedelta, timezone
from cache            import cache_get, cache_set, KEYS, TTL

router = APIRouter()

@router.get("/live")
def live_metrics(db: Session = Depends(get_db)):
    """FR-6.1: Last 5 minutes of raw metric samples. Redis-cached for 10s."""
    cached = cache_get(KEYS["metrics_live"])
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    samples = db.query(MetricSample).filter(MetricSample.timestamp >= cutoff).order_by(MetricSample.timestamp.asc()).all()
    result = [
        {
            "id": s.id,
            "timestamp": s.timestamp.isoformat() if s.timestamp else datetime.now(timezone.utc).isoformat(),
            "service": s.service,
            "metric_type": s.metric_type,
            "value": float(s.value),
        }
        for s in samples
    ]
    cache_set(KEYS["metrics_live"], result, TTL["metrics_live"])
    return result


@router.get("/anomalies/active")
def active_anomalies(db: Session = Depends(get_db)):
    """FR-6.1: Anomalies detected in the last 2 minutes. Redis-cached for 6s."""
    cached = cache_get(KEYS["anomalies_active"])
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    anomalies = (
        db.query(Anomaly)
        .options(joinedload(Anomaly.metric_sample))
        .filter(Anomaly.detected_at >= cutoff)
        .order_by(Anomaly.detected_at.desc())
        .all()
    )
    result = [
        {
            "id": a.id,
            "metric_sample_id": a.metric_sample_id,
            "service": a.metric_sample.service if a.metric_sample else "payment-service",
            "metric_type": a.metric_sample.metric_type if a.metric_sample else "cpu",
            "score": float(a.score),
            "severity": a.severity,
            "detected_at": a.detected_at.isoformat() if a.detected_at else datetime.now(timezone.utc).isoformat(),
        }
        for a in anomalies
    ]
    cache_set(KEYS["anomalies_active"], result, TTL["anomalies_active"])
    return result
