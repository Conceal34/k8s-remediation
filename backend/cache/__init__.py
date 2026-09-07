# backend/cache/__init__.py
"""
Redis Cache Layer — FR-NFR-6: Scalability & Incident Caching
Provides:
1. Telemetry & Decision query caching with TTL and event-driven invalidation.
2. Incident Reasoning Cache — Caches Gemini agent outputs (Diagnosis, Remediation, Critic)
   by incident signature (service + metric_type) to reduce API calls by up to 90%.
"""
import json
import redis
import os
from typing import Any, Optional

# ── Connection ────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Returns the singleton Redis client, or None if Redis is unavailable."""
    global _client
    if _client is not None:
        return _client
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        r.ping()
        _client = r
        print("[Redis] ✓ Connected to Redis cache.")
        return _client
    except Exception as e:
        print(f"[Redis] ⚠️  Redis unavailable ({e}). Falling back to direct DB queries.")
        return None


# ── Cache Keys ────────────────────────────────────────────────────────────────
KEYS = {
    "metrics_live":       "cache:metrics:live",
    "anomalies_active":   "cache:anomalies:active",
    "decisions_list":     "cache:decisions:list",
    "decisions_escalated": "cache:decisions:escalated",
}

# TTLs (seconds) — how long cached data is considered fresh
TTL = {
    "metrics_live":        10,   # Matches collector polling interval
    "anomalies_active":    8,
    "decisions_list":      6,
    "decisions_escalated": 6,
    "incident_reasoning":  3600, # 1 hour incident reasoning cache
}


# ── Core helpers ──────────────────────────────────────────────────────────────
def cache_get(key: str) -> Optional[Any]:
    """Get a cached value. Returns deserialized Python object or None on miss/error."""
    r = get_redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    """Store a value in Redis with a TTL. Silently skips if Redis is down."""
    r = get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_invalidate(*keys: str) -> None:
    """Delete one or more cache keys, forcing the next read to hit the DB."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(*keys)
    except Exception:
        pass


def invalidate_decision_caches() -> None:
    """Called after any new Decision or Anomaly is written to the DB."""
    cache_invalidate(
        KEYS["decisions_list"],
        KEYS["decisions_escalated"],
        KEYS["anomalies_active"],
    )
    try:
        r = get_redis()
        if r:
            r.publish("decisions.new", "1")
    except Exception:
        pass


def invalidate_metrics_cache() -> None:
    """Called after every MetricsCollector write tick."""
    cache_invalidate(KEYS["metrics_live"])


# ── Incident Reasoning Cache (Saves Gemini Tokens & Quota) ────────────────────
def get_incident_cache(service: str, metric_type: str, stage: str) -> Optional[Any]:
    """
    Checks Redis for previously computed Gemini reasoning for (service, metric_type, stage).
    Returns cached result or None if miss.
    """
    key = f"cache:incident:{service}:{metric_type}:{stage}"
    return cache_get(key)


def set_incident_cache(service: str, metric_type: str, stage: str, data: Any, ttl: int = 3600) -> None:
    """
    Caches Gemini agent outputs in Redis for future recurring incidents.
    """
    key = f"cache:incident:{service}:{metric_type}:{stage}"
    cache_set(key, data, ttl)
