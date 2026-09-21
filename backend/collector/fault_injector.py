# backend/collector/fault_injector.py
"""
Fault Injector — FR-1.3
Creates anomaly-generating pods in Kubernetes on demand for demo sessions.
Also maintains an active fault state so telemetry stays anomalous until remediated.
Usage: python fault_injector.py [crash_loop | memory_spike | cpu_spike | cleanup | --db-only]
"""

import os, sys, subprocess, time, json

# Auto-activate virtualenv if run from host python
_venv_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.venv/bin/python3"))
if os.path.exists(_venv_py) and sys.executable != _venv_py:
    os.execv(_venv_py, [_venv_py] + sys.argv)

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# ── Fault manifests ───────────────────────────────────────────────────────────
MANIFESTS = {
    "crash_loop": """
apiVersion: v1
kind: Pod
metadata:
  name: fault-crash-loop
  namespace: default
  labels:
    app: payment-service
    fault: crash-loop
spec:
  containers:
  - name: crash
    image: busybox
    command: ["sh", "-c", "echo 'Crashing...' && exit 1"]
  restartPolicy: Always
""",
    "memory_spike": """
apiVersion: v1
kind: Pod
metadata:
  name: fault-memory-spike
  namespace: default
  labels:
    app: payment-service
    fault: memory-spike
spec:
  containers:
  - name: stress
    image: polinux/stress
    command: ["stress", "--vm", "1", "--vm-bytes", "200M", "--vm-hang", "120"]
    resources:
      limits:
        memory: "256Mi"
""",
    "cpu_spike": """
apiVersion: v1
kind: Pod
metadata:
  name: fault-cpu-spike
  namespace: default
  labels:
    app: payment-service
    fault: cpu-spike
spec:
  containers:
  - name: stress
    image: polinux/stress
    command: ["stress", "--cpu", "2", "--timeout", "90s"]
    resources:
      limits:
        cpu: "400m"
""",
}

FAULT_POD_NAMES = ["fault-crash-loop", "fault-memory-spike", "fault-cpu-spike"]

# ── Anomalous metric values for DB injection ───────────────────────────────────
ANOMALY_VALUES = {
    "crash_loop":    {"cpu": 18.0,  "memory": 35.0,  "restarts": 14, "error_rate": 0.88},
    "memory_spike":  {"cpu": 42.0,  "memory": 94.0,  "restarts": 0,  "error_rate": 0.06},
    "cpu_spike":     {"cpu": 96.0,  "memory": 40.0,  "restarts": 0,  "error_rate": 0.04},
}

STATE_FILE = os.path.join(os.path.dirname(__file__), ".active_faults.json")


# ── Active Fault State Helpers ────────────────────────────────────────────────
def set_active_fault(service: str, fault_type: str):
    """Sets active persistent fault state in Redis and local state file."""
    vals = ANOMALY_VALUES.get(fault_type, {})
    payload = {"fault_type": fault_type, "values": vals, "timestamp": time.time()}
    try:
        from cache import get_redis
        r = get_redis()
        if r:
            r.setex(f"active_fault:{service}", 180, json.dumps(payload))
    except Exception:
        pass

    try:
        current = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                current = json.load(f)
        current[service] = payload
        with open(STATE_FILE, "w") as f:
            json.dump(current, f)
    except Exception:
        pass


def get_active_fault(service: str) -> dict | None:
    """Returns active fault for service if present, else None."""
    try:
        from cache import get_redis
        r = get_redis()
        if r:
            raw = r.get(f"active_fault:{service}")
            if raw:
                return json.loads(raw).get("values")
    except Exception:
        pass

    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                current = json.load(f)
            data = current.get(service)
            if data and (time.time() - data.get("timestamp", 0) < 180):
                return data.get("values")
    except Exception:
        pass
    return None


def clear_active_fault(service: str | None = None):
    """Clears active fault state (called when incident is remediated)."""
    try:
        from cache import get_redis
        r = get_redis()
        if r:
            if service:
                r.delete(f"active_fault:{service}")
                r.delete(f"pipeline_cooldown:{service}")
            else:
                for s in ["payment-service", "order-service", "auth-service"]:
                    r.delete(f"active_fault:{s}")
                    r.delete(f"pipeline_cooldown:{s}")
    except Exception:
        pass

    # Bug 7 Fix: immediately bust anomalies_active cache so KPI card resets
    try:
        from cache import cache_invalidate, KEYS
        cache_invalidate(KEYS["anomalies_active"])
    except Exception:
        pass

    try:
        if service and os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                current = json.load(f)
            current.pop(service, None)
            with open(STATE_FILE, "w") as f:
                json.dump(current, f)
        elif not service and os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except Exception:
        pass


# ── Kubernetes Injection ───────────────────────────────────────────────────────
def inject_k8s(fault_type: str):
    """Injects fault via kubectl apply."""
    if fault_type not in MANIFESTS:
        print(f"Unknown fault: {fault_type}. Options: {list(MANIFESTS.keys())}")
        return False
    result = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=MANIFESTS[fault_type].encode(),
        capture_output=True
    )
    stdout = result.stdout.decode().strip()
    stderr = result.stderr.decode().strip()

    if result.returncode == 0:
        if stdout:
            print(stdout)
        print(f"[FaultInjector] ✓ Kubernetes chaos pod deployed: {fault_type}")
        return True
    else:
        # Silently ignore "connection refused" — expected in simulated / no-cluster mode
        if "connection refused" in stderr.lower() or "connect: connection refused" in stderr.lower():
            print(f"[FaultInjector] ℹ  No K8s cluster reachable — running in simulated mode (fault active via Redis/DB).")
        else:
            print(f"[FaultInjector] ⚠  kubectl error: {stderr}")
        return False


# ── Database Injection ─────────────────────────────────────────────────────────
VALID_SERVICES = ["payment-service", "order-service", "auth-service"]

def inject_db(fault_type: str, service: str = "payment-service"):
    """Inserts anomalous MetricSamples and enables persistent active fault state on the given service."""
    from database.session import SessionLocal
    from database.models import MetricSample
    from datetime import datetime, timezone

    if fault_type not in ANOMALY_VALUES:
        print(f"Unknown fault: {fault_type}. Options: {list(ANOMALY_VALUES.keys())}")
        return
    if service not in VALID_SERVICES:
        print(f"Unknown service: {service}. Options: {VALID_SERVICES}")
        return

    vals = ANOMALY_VALUES[fault_type]
    ts   = datetime.now(timezone.utc)
    db   = SessionLocal()

    # Enable persistent active fault so telemetry stays anomalous until healed
    set_active_fault(service, fault_type)

    rows = [
        MetricSample(timestamp=ts, service=service, metric_type="cpu",        value=vals["cpu"]),
        MetricSample(timestamp=ts, service=service, metric_type="memory",     value=vals["memory"]),
        MetricSample(timestamp=ts, service=service, metric_type="restarts",   value=vals["restarts"]),
        MetricSample(timestamp=ts, service=service, metric_type="error_rate", value=vals["error_rate"]),
    ]
    db.add_all(rows)
    db.commit()
    db.close()

    # Invalidate live metrics cache immediately
    try:
        from cache import invalidate_metrics_cache, invalidate_decision_caches
        invalidate_metrics_cache()
        invalidate_decision_caches()
    except Exception:
        pass

    print(f"[FaultInjector] ✓ Activated incident state for: {fault_type} on {service}")
    print(f"  cpu={vals['cpu']}%  memory={vals['memory']}%  restarts={vals['restarts']}  error_rate={vals['error_rate']}")
    print(f"  [!] Telemetry will STAY anomalous until autonomous remediation resolves it.")


def inject(fault_type: str, service: str = "payment-service", db_only: bool = False):
    """Main injection entrypoint. Sets active fault state AND applies K8s manifest."""
    inject_db(fault_type, service=service)
    if not db_only:
        try:
            inject_k8s(fault_type)
        except Exception:
            pass


def cleanup():
    """Remove fault pods and clear active fault states."""
    clear_active_fault()
    for name in FAULT_POD_NAMES:
        try:
            subprocess.run(
                ["kubectl", "delete", "pod", name, "--ignore-not-found", "--grace-period=0"],
                capture_output=True
            )
        except FileNotFoundError:
            pass # kubectl not installed (simulated mode)
        except Exception:
            pass
    # Invalidate caches
    try:
        from cache import invalidate_metrics_cache, invalidate_decision_caches
        invalidate_metrics_cache()
        invalidate_decision_caches()
    except Exception:
        pass
    print("[FaultInjector] ✓ Active faults cleared & cleanup complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Fault Injector — inject synthetic anomalies into the CloudOps cluster."
    )
    parser.add_argument(
        "fault_type",
        choices=list(ANOMALY_VALUES.keys()) + ["cleanup"],
        help="Fault to inject, or 'cleanup' to clear all faults."
    )
    parser.add_argument(
        "--service", "-s",
        default="payment-service",
        choices=VALID_SERVICES,
        help="Target service (default: payment-service)"
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Skip kubectl manifest apply, only update DB + Redis state."
    )
    args = parser.parse_args()

    if args.fault_type == "cleanup":
        cleanup()
    else:
        inject(args.fault_type, service=args.service, db_only=args.db_only)
