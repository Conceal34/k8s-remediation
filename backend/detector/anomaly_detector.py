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

        # contamination=0.01 means model expects only ~1% of data to be anomalous.
        # This prevents it from flagging normal baseline readings as anomalies.
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.01,   # was 0.05 — caused ~5% of normal data to fire as anomalies
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
        context: recent MetricSample rows used to build the feature vector.
        """
        if self.model is None:
            return None

        # Require the model to have seen enough normal data before it starts firing.
        # Without this guard, a model trained on only a few rows will misfire.
        if self._trained_rows < 30:
            return None

        # Build feature vector for this service using its most recent context rows
        vec = [0.0, 0.0, 0.0, 0.0]
        for s in context:
            if s.service == sample.service:
                idx = METRIC_IDX.get(s.metric_type)
                if idx is not None:
                    vec[idx] = float(s.value)

        X = np.array([vec])
        prediction = self.model.predict(X)[0]       # -1 = anomaly, 1 = normal

        if prediction != -1:
            return None

        # sklearn's score_samples() returns negative values.
        # Typical range for IsolationForest: roughly [-0.5, 0.5].
        # More negative = more isolated = more anomalous.
        # We map to [0, 1] where 1 = maximally anomalous.
        raw_score  = self.model.score_samples(X)[0]
        # Clamp raw_score to expected range then invert: -0.5 → 1.0, 0.0 → 0.5, 0.5 → 0.0
        normalized = float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0))

        if normalized < THRESHOLD:
            return None

        severity = self._assign_severity(normalized)
        return normalized, severity

    def _assign_severity(self, score: float) -> str:
        """FR-2.3: Map score to low / medium / high severity band."""
        for label, bounds in SEVERITY_BANDS.items():
            lo, hi = bounds
            if lo <= score < hi:
                return label
        return "high"

    # ── Persistence ───────────────────────────────────────────────────────────
    def persist_anomaly(self, sample: MetricSample, score: float, severity: str) -> Anomaly:
        """Write Anomaly row + audit log entry to DB."""
        db = SessionLocal()
        try:
            anomaly = Anomaly(
                metric_sample_id=sample.id,
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
                detail={"score": round(score, 4), "severity": severity, "service": sample.service},
                timestamp=datetime.now(timezone.utc),
            )
            db.add(audit)
            db.commit()
            db.refresh(anomaly)
            print(f"[AnomalyDetector] ⚠️  ANOMALY: service={sample.service} score={score:.3f} severity={severity}")
            return anomaly
        finally:
            db.close()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _fetch_window(self, minutes: int) -> list[MetricSample]:
        db     = SessionLocal()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        rows   = db.query(MetricSample).filter(MetricSample.timestamp >= cutoff).all()
        if len(rows) < 20:
            rows = db.query(MetricSample).order_by(MetricSample.timestamp.desc()).limit(1000).all()
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
        X    = np.array([bucket[k] for k in keys]) if keys else np.empty((0, 4))
        return X, keys


# Module-level singleton used by the metrics collector
detector = AnomalyDetector()
