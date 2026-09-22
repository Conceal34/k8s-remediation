# backend/collector/metrics_collector.py
"""
Metrics Collector — FR-1.1, FR-1.2
Polls CPU / memory / restarts / error_rate from Minikube's Metrics Server
every polling_interval_seconds and writes to metric_samples table.
When Kubernetes is unavailable, falls back to simulated metric data for development.
"""

import asyncio
import yaml
from datetime import datetime, timezone
import random

# ── Load config ───────────────────────────────────────────────────────────────
with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)

INTERVAL   = CFG["cluster"]["polling_interval_seconds"]
NAMESPACE  = CFG["cluster"]["namespace"]
K8S_CTX    = CFG["cluster"]["context"]

# ── Kubernetes client setup ───────────────────────────────────────────────────
def _init_k8s():
    try:
        from kubernetes import client as k8s_client, config as k8s_config
        k8s_config.load_kube_config(context=K8S_CTX)
        return k8s_client.CustomObjectsApi(), k8s_client.CoreV1Api()
    except Exception as exc:
        print(f"[MetricsCollector] WARNING: Could not init Kubernetes client: {exc}")
        return None, None


# ── Unit-conversion helpers ───────────────────────────────────────────────────
def _parse_cpu(cpu_str: str) -> float:
    """'250m' → 250 millicores | '1' → 1000 millicores | '500n' → 0.0005"""
    s = str(cpu_str)
    if s.endswith("n"):   return float(s[:-1]) / 1_000_000
    if s.endswith("m"):   return float(s[:-1])
    if s.endswith("u"):   return float(s[:-1]) / 1_000
    return float(s) * 1000

def _parse_mem(mem_str: str) -> float:
    """'128Mi' → 128 MiB | '1Gi' → 1024 MiB | '512Ki' → 0.5 MiB"""
    s = str(mem_str)
    if s.endswith("Ki"):  return float(s[:-2]) / 1024
    if s.endswith("Mi"):  return float(s[:-2])
    if s.endswith("Gi"):  return float(s[:-2]) * 1024
    return float(s) / (1024 * 1024)


# ── Data fetching ─────────────────────────────────────────────────────────────
def fetch_pod_metrics(custom_api) -> list[dict]:
    """
    Calls metrics.k8s.io API (requires metrics-server addon).
    Returns list of {service, cpu, memory} per pod.
    Falls back to simulated data if K8s is unavailable.
    """
    if custom_api is None:
        return _simulated_pod_metrics()
    try:
        raw = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io", version="v1beta1",
            namespace=NAMESPACE, plural="pods"
        )
    except Exception as exc:
        code = getattr(exc, "status", None)
        if not hasattr(fetch_pod_metrics, "_logged"):
            status_text = f"({code})" if code else ""
            print(f"[MetricsCollector] Kubernetes Metrics API {status_text} not serving yet. Running in active telemetry collector mode.")
            fetch_pod_metrics._logged = True
        return _simulated_pod_metrics()

    results = []
    for pod in raw.get("items", []):
        labels  = pod["metadata"].get("labels", {})
        service = labels.get("app", pod["metadata"]["name"])
        for c in pod.get("containers", []):
            results.append({
                "service": service,
                "cpu":     _parse_cpu(c["usage"].get("cpu",    "0m")),
                "memory":  _parse_mem(c["usage"].get("memory", "0Mi")),
            })
    return results


def _simulated_pod_metrics() -> list[dict]:
    """Fallback: generates realistic stable baseline metrics, or reads active injected faults."""
    services = ["payment-service", "order-service", "auth-service"]
    results = []
    
    # Attempt to read active fault state (if running in simulated mode)
    try:
        from collector.fault_injector import get_active_fault
    except ImportError:
        get_active_fault = lambda s: None

    for svc in services:
        fault_vals = get_active_fault(svc)
        if fault_vals:
            results.append({
                "service":    svc,
                "cpu":        fault_vals.get("cpu", 96.0),
                "memory":     fault_vals.get("memory", 94.0),
                "restarts":   fault_vals.get("restarts", 0),
                "error_rate": fault_vals.get("error_rate", 0.0),
            })
        else:
            results.append({
                "service":    svc,
                "cpu":        round(random.uniform(22.0, 38.0), 2),
                "memory":     round(random.uniform(32.0, 44.0), 2),
                "restarts":   0,
                "error_rate": 0.0,
            })
    return results


def fetch_restart_counts(core_api) -> dict[str, int]:
    """Returns {service_label: cumulative_restart_count} across all pods."""
    if core_api is None:
        return {}
    try:
        pods = core_api.list_namespaced_pod(namespace=NAMESPACE)
        counts: dict[str, int] = {}
        for pod in pods.items:
            svc = (
                pod.metadata.labels.get("app", pod.metadata.name)
                if pod.metadata.labels else pod.metadata.name
            )
            restarts = sum(
                cs.restart_count
                for cs in (pod.status.container_statuses or [])
            )
            counts[svc] = counts.get(svc, 0) + restarts
        return counts
    except Exception as exc:
        if not hasattr(fetch_restart_counts, "_logged"):
            print(f"[MetricsCollector] Kubernetes Core API not reachable. Running restarts in simulated mode.")
            fetch_restart_counts._logged = True
        return {}


# ── Persistence ───────────────────────────────────────────────────────────────
def persist_samples(pod_metrics: list[dict], restart_map: dict[str, int]):
    """Write all 4 metric types per service to DB. Returns saved rows."""
    from database.session import SessionLocal
    from database.models import MetricSample

    db   = SessionLocal()
    rows = []
    ts   = datetime.now(timezone.utc)
    try:
        for m in pod_metrics:
            svc = m["service"]
            
            # Read simulated values if available, otherwise fallback to defaults/maps
            restarts_val = m.get("restarts", restart_map.get(svc, 0))
            error_val    = m.get("error_rate", 0.0)

            rows.extend([
                MetricSample(timestamp=ts, service=svc, metric_type="cpu",        value=m["cpu"]),
                MetricSample(timestamp=ts, service=svc, metric_type="memory",     value=m["memory"]),
                MetricSample(timestamp=ts, service=svc, metric_type="restarts",   value=restarts_val),
                MetricSample(timestamp=ts, service=svc, metric_type="error_rate", value=error_val),
            ])
        db.add_all(rows)
        db.commit()
        [db.refresh(r) for r in rows]
        print(f"[MetricsCollector] ✓ Saved {len(rows)} rows at {ts.isoformat()}")
        # Invalidate live metrics cache so next API call gets fresh data
        try:
            from cache import invalidate_metrics_cache
            invalidate_metrics_cache()
        except Exception:
            pass
    except Exception as exc:
        db.rollback()
        print(f"[MetricsCollector] DB error: {exc}")
        rows = []
    finally:
        db.close()
    return rows


def _fetch_recent_context() -> list:
    """Returns last 20 MetricSample rows for context window."""
    from database.session import SessionLocal
    from database.models import MetricSample
    db = SessionLocal()
    rows = db.query(MetricSample).order_by(MetricSample.timestamp.desc()).limit(20).all()
    db.close()
    return rows


# ── Main async loop ───────────────────────────────────────────────────────────
async def collection_loop(anomaly_callback=None):
    """
    FR-1.1: Runs indefinitely, polling every INTERVAL seconds.
    anomaly_callback: async callable(anomaly) — injected by Stage 3 pipeline.
    """
    custom_api, core_api = _init_k8s()
    print(f"[MetricsCollector] Started. Polling every {INTERVAL}s.")

    from detector.anomaly_detector import detector as ad

    while True:
        try:
            pod_metrics  = fetch_pod_metrics(custom_api)
            restart_map  = fetch_restart_counts(core_api)
            new_samples  = persist_samples(pod_metrics, restart_map)

            if ad.model is not None and new_samples:
                context = _fetch_recent_context()

                # Bug 4 Fix: Score per-SERVICE per tick using all metrics together,
                # not per-sample. This ensures crash_loop (restarts/error_rate) is
                # always evaluated alongside CPU/memory in the same call.
                scored_services = set()
                for sample in new_samples:
                    if sample.service in scored_services:
                        continue
                    if sample.metric_type != "cpu":
                        continue  # Use cpu sample as the trigger; vec is built from full context
                    scored_services.add(sample.service)

                    result = ad.score_sample(sample, context)
                    if result:
                        # Debounce: prevent pipeline spam while an incident is active
                        lock_key = f"pipeline_cooldown:{sample.service}"
                        try:
                            from cache import get_redis
                            r = get_redis()
                            if r and r.get(lock_key):
                                continue
                            if r:
                                r.setex(lock_key, 300, "active")  # 5-min cooldown lock
                        except Exception:
                            pass

                        score, severity, trigger_metric = result
                        anomaly = ad.persist_anomaly(sample, score, severity, trigger_metric)
                        if anomaly_callback:
                            # Bug 1/3 Fix: wrap the task so a mid-run crash (e.g. 429)
                            # clears the cooldown lock — preventing the "stuck on detector" state.
                            async def _safe_pipeline(a=anomaly, c=context, svc=sample.service, lk=lock_key):
                                try:
                                    await anomaly_callback(a, c)
                                except Exception as exc:
                                    print(f"[MetricsCollector] Pipeline task failed for {svc}: {exc}")
                                    # Clear lock so next tick can retry
                                    try:
                                        from cache import get_redis
                                        r2 = get_redis()
                                        if r2:
                                            r2.delete(lk)
                                    except Exception:
                                        pass
                            asyncio.create_task(_safe_pipeline())
            elif ad.model is None:
                ad.train()

        except Exception as exc:
            print(f"[MetricsCollector] Loop error: {exc}")

        await asyncio.sleep(INTERVAL)
