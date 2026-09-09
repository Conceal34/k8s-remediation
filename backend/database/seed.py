import sys
import os
import random
from datetime import datetime, timedelta, timezone

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import SessionLocal
from database.models import MetricSample

def seed_baseline_data(hours=12):
    db = SessionLocal()
    
    # Check if we already have enough data to avoid long startup times
    count = db.query(MetricSample).count()
    if count > 2000:
        print(f"[Seed] DB already has {count} metric samples. Skipping baseline seed.")
        db.close()
        return

    print(f"[Seed] Generating {hours} hours of clean baseline telemetry to train Isolation Forest...")
    services = ["payment-service", "order-service", "auth-service"]
    now = datetime.now(timezone.utc)
    
    rows = []
    for m in range(hours * 60):
        ts = now - timedelta(minutes=m+5) # offset to avoid overlapping with live data
        for svc in services:
            rows.extend([
                MetricSample(timestamp=ts, service=svc, metric_type="cpu",        value=round(random.uniform(22.0, 38.0), 2)),
                MetricSample(timestamp=ts, service=svc, metric_type="memory",     value=round(random.uniform(32.0, 44.0), 2)),
                MetricSample(timestamp=ts, service=svc, metric_type="restarts",   value=0),
                MetricSample(timestamp=ts, service=svc, metric_type="error_rate", value=0.0),
            ])
            
            if len(rows) >= 2000:
                db.add_all(rows)
                db.commit()
                rows = []

    if rows:
        db.add_all(rows)
        db.commit()
        
    final_count = db.query(MetricSample).count()
    print(f"[Seed] ✓ Successfully seeded baseline data. Total samples: {final_count}")
    db.close()

if __name__ == "__main__":
    seed_baseline_data()
