#!/bin/bash
set -e
cd "$(dirname "$0")/.."    # Run from project root

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Agentic CloudOps — Full Demo Run           ║"
echo "║   Vinner Hooda | MCA Capstone                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

echo "[1/6] Cleaning previous fault pods..."
python3 backend/collector/fault_injector.py cleanup 2>/dev/null || true

echo "[2/6] Checking 4-Node Kubernetes Cluster (1 Control Plane + 3 Workers)..."
kubectl get nodes -o wide

echo "[3/6] Checking payment-service deployment..."
kubectl get deployment payment-service

echo "[4/6] Checking PostgreSQL..."
podman exec -it $(podman ps -qf "ancestor=postgres:16-alpine") psql -U cloudops -d cloudops_db -c "SELECT COUNT(*) AS decisions FROM decisions;" 2>/dev/null || echo "  (No decisions yet)"

echo "[5/6] Opening dashboard at http://localhost:5173 ..."
xdg-open http://localhost:5173 2>/dev/null &

# Start backend (1 worker = lower RAM, single-threaded async is enough for demo)
echo "[*] Starting FastAPI backend..."
(cd "$(dirname "$0")/.." && source .venv/bin/activate &&
  export PYTHONPATH=$PWD/backend &&
  export MALLOC_TRIM_THRESHOLD_=65536 &&
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    --workers 1 --loop asyncio --no-access-log &
)
sleep 2

# Start frontend (Vite dev server)
echo "[*] Starting Vite frontend..."
(cd "$(dirname "$0")/../frontend" && npm run dev -- --host 0.0.0.0 &)
sleep 2

echo ""
echo "[6/6] Injecting CPU spike anomaly in 5 seconds..."
sleep 5
python3 backend/collector/fault_injector.py cpu_spike

echo ""
echo "Anomaly injected. Watch the dashboard — pipeline will run within ~10 seconds."
echo ""
echo "Waiting 40 seconds then showing audit log..."
sleep 40

echo ""
echo "── Recent Audit Log ─────────────────────────────────────────────"
podman exec -it $(podman ps -qf "ancestor=postgres:16-alpine") psql -U cloudops -d cloudops_db -c "SELECT event, timestamp FROM audit_log_entries ORDER BY timestamp DESC LIMIT 12;"
# Ignore error on cleanup so audit log stays visible if needed
python3 backend/collector/fault_injector.py cleanup || true
echo "─────────────────────────────────────────────────────────────────"

echo ""
echo "[DONE] Check dashboard for the full decision trail."
