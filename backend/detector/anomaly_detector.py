# backend/detector/anomaly_detector.py
"""
Anomaly Detector — FR-2.1, FR-2.2, FR-2.3
Trains Isolation Forest on normal metric data.
Scores new samples; flags anomalies and assigns severity.
"""

import yaml
import numpy as np
from collections import defaultdict
from sklearn.ensemble import IsolationForest
from database.session import SessionLocal
from database.models import MetricSample, Anomaly, AuditLogEntry
from datetime import datetime, timedelta, timezone


with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)

THRESHOLD      = CFG["anomaly_detection"]["anomaly_score_threshold"]
SEVERITY_BANDS = CFG["anomaly_detection"]["severity_bands"]
TRAIN_MINUTES  = CFG["anomaly_detection"]["training_window_minutes"]

METRIC_IDX = {"cpu": 0, "memory": 1, "restarts": 2, "error_rate": 3}


class AnomalyDetector:
    def __init__(self):
        self.model: IsolationForest | None = None
        self._trained_rows: int = 0

    # ── Training ──────────────────────────────────────────────────────────────
    def train(self) -> bool:
        """FR-2.1: Train on the last TRAIN_MINUTES of metric data from DB."""
        samples = self._fetch_window(TRAIN_MINUTES)
        if len(samples) < 20:
            print(f"[AnomalyDetector] Not enough training data ({len(samples)} rows). Waiting...")
            return False

        X, _ = self._build_feature_matrix(samples)
        if X.shape[0] < 10:
            return False

        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,   # 5% boundary — controls decision_function threshold
            random_state=42,
        )
        self.model.fit(X)
        self._trained_rows = X.shape[0]
        print(f"[AnomalyDetector] ✓ Model trained on {X.shape[0]} feature vectors.")
        return True

    # ── Scoring ───────────────────────────────────────────────────────────────
    def score_sample(self, sample: MetricSample, context: list[MetricSample]) -> tuple[float, str] | None:
        """
        FR-2.2: Score a new sample. Returns (score, severity) if anomalous, else None.
        Uses decision_function() which has a clean boundary at 0:
          > 0 = normal,  < 0 = anomaly (magnitude = how anomalous).
        This avoids the false-positive problem of predict() with contamination=0.05.
        """
        if self.model is None:
            return None

        # Don't score until the model has seen enough distinct samples.
        if self._trained_rows < 5:
            return None

        # Build feature vector for this service
        vec = [0.0, 0.0, 0.0, 0.0]
        # First, populate from historical context (sorted newest-first)
        # Only take the first (newest) value for each metric type to avoid older ticks overwriting new ones
        seen = set()
        for s in context:
            if s.service == sample.service:
                idx = METRIC_IDX.get(s.metric_type)
                if idx is not None and idx not in seen:
                    vec[idx] = float(s.value)
                    seen.add(idx)
                    
        # Then OVERRIDE with the actual live incoming sample!
        idx = METRIC_IDX.get(sample.metric_type)
        if idx is not None:
            vec[idx] = float(sample.value)

        # 1. Deterministic Rule-Based Checks
        cpu = vec[0]
        memory = vec[1]
        restarts = vec[2]
        error_rate = vec[3]

        if cpu > 75.0:
            return 0.98, "high", "cpu"
        if memory > 75.0:
            return 0.98, "high", "memory"
        if restarts > 3:
            return 0.95, "high", "restarts"
        if error_rate > 0.10:
            return 0.90, "high", "error_rate"

        # 2. AI-Driven Check — only fires for extreme ML outliers
        X = np.array([vec])
        df = float(self.model.decision_function(X)[0])

        if df >= -0.15:
            return None

        normalized = float(np.clip(-df / 0.20, 0.0, 1.0))
        severity = self._assign_severity(normalized)
        
        # Determine primary contributor for ML anomalies
        trigger_metric = "composite"
        if cpu > 40: trigger_metric = "cpu"
        elif memory > 50: trigger_metric = "memory"
        elif restarts > 0: trigger_metric = "restarts"
        elif error_rate > 0.02: trigger_metric = "error_rate"
            
        return normalized, severity, trigger_metric

    def _assign_severity(self, score: float) -> str:
        """FR-2.3: Map score to low / medium / high severity band."""
        for label, bounds in SEVERITY_BANDS.items():
            lo, hi = bounds
            if lo <= score < hi:
                return label
        return "high"

    # ── Persistence ───────────────────────────────────────────────────────────
    def persist_anomaly(self, sample: MetricSample, score: float, severity: str, trigger_metric: str) -> Anomaly:
        """Write Anomaly row + audit log entry to DB. Uses correct trigger_metric."""
        db = SessionLocal()
        try:
            # If the trigger metric is different from the 'trigger sample' passed in (usually cpu),
            # try to find the actual sample row from the same timestamp bucket
            target_sample_id = sample.id
            if trigger_metric != sample.metric_type and trigger_metric != "composite":
                # Find the sample for this service with the trigger metric from the same time
                ts = sample.timestamp
                actual_sample = db.query(MetricSample).filter(
                    MetricSample.service == sample.service,
                    MetricSample.metric_type == trigger_metric,
                    MetricSample.timestamp == ts
                ).first()
                if actual_sample:
                    target_sample_id = actual_sample.id

            anomaly = Anomaly(
                metric_sample_id=target_sample_id,
                score=round(score, 6),
                severity=severity,
                detected_at=datetime.now(timezone.utc),
            )
            db.add(anomaly)
            db.flush()

            audit = AuditLogEntry(
                ref_type="anomaly",
                ref_id=anomaly.id,
                event="anomaly_detected",
                detail={"score": round(score, 4), "severity": severity, "service": sample.service, "metric": trigger_metric},
                timestamp=datetime.now(timezone.utc),
            )
            db.add(audit)
            db.commit()
            db.refresh(anomaly)
            print(f"[AnomalyDetector] ⚠️  ANOMALY: service={sample.service} metric={trigger_metric} score={score:.3f} severity={severity}")
            return anomaly
        finally:
            db.close()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _fetch_window(self, minutes: int) -> list[MetricSample]:
        db     = SessionLocal()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        rows   = db.query(MetricSample).filter(MetricSample.timestamp >= cutoff).all()
        # If the time window doesn't capture a healthy baseline (e.g. after a long pause),
        # fallback to grabbing the most recent 10,000 samples to ensure we hit the seeded data.
        if len(rows) < 4000:
            rows = db.query(MetricSample).order_by(MetricSample.timestamp.desc()).limit(10000).all()
        db.close()
        return rows

    def _build_feature_matrix(self, samples: list[MetricSample]) -> tuple[np.ndarray, list]:
        """Groups by (minute-bucket, service) and builds [cpu, memory, restarts, error_rate] rows."""
        bucket = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
        for s in samples:
            ts_key = s.timestamp.replace(second=0, microsecond=0)
            key    = (ts_key, s.service)
            idx    = METRIC_IDX.get(s.metric_type)
            if idx is not None:
                bucket[key][idx] = float(s.value)

        keys = sorted(bucket.keys())
        # Filter out extreme injected faults from training data to prevent model drift
        valid_keys = [k for k in keys if bucket[k][0] < 80.0 and bucket[k][1] < 80.0 and bucket[k][2] == 0]
        X    = np.array([bucket[k] for k in valid_keys]) if valid_keys else np.empty((0, 4))
        return X, valid_keys


# Module-level singleton used by the metrics collector
detector = AnomalyDetector()
