# scripts/seed_normal_data.py
"""
Seeds 10 minutes of synthetic normal-operation metric data.
Run this ONCE before starting the collector for the first time.
Isolation Forest needs a clean baseline to learn what "normal" looks like.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database.session import SessionLocal, create_tables
from backend.database.models import MetricSample
from datetime import datetime, timedelta, timezone
import random

create_tables()

SERVICES = ["payment-service", "order-service", "auth-service"]

NORMAL_RANGES = {
    "cpu":        (22.0, 38.0),    # CPU percentage (22-38%)
    "memory":     (32.0, 44.0),    # Memory percentage (32-44%)
    "restarts":   (0.0, 0.0),
    "error_rate": (0.001, 0.015),
}


def seed():
    db      = SessionLocal()
    base_ts = datetime.now(timezone.utc) - timedelta(minutes=10)
    rows    = []

    for tick in range(60):                        # 60 ticks × 10s = 10 minutes
        ts = base_ts + timedelta(seconds=tick * 10)
        for svc in SERVICES:
            for metric_type, (lo, hi) in NORMAL_RANGES.items():
                rows.append(MetricSample(
                    timestamp   = ts,
                    service     = svc,
                    metric_type = metric_type,
                    value       = round(random.uniform(lo, hi), 4),
                ))

    db.add_all(rows)
    db.commit()
    db.close()
    print(f"[Seed] ✓ Inserted {len(rows)} normal metric rows across {len(SERVICES)} services.")


if __name__ == "__main__":
    seed()
