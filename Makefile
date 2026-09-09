.PHONY: backend frontend clean flush-cache reset inject-cpu inject-memory inject-crash

backend:
	PYTHONPATH=$(PWD)/backend .venv/bin/python3 backend/database/seed.py
	PYTHONPATH=$(PWD)/backend .venv/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

clean:
	.venv/bin/python3 backend/collector/fault_injector.py cleanup

flush-cache:
	@echo "Flushing Redis incident reasoning caches..."
	.venv/bin/python3 -c "import redis; r=redis.from_url('redis://localhost:6379/0', decode_responses=True); keys=r.keys('cache:incident:*'); r.delete(*keys) if keys else None; print(f'Flushed {len(keys)} reasoning cache keys.')"

reset: clean flush-cache
	@echo "Full reset complete — faults cleared, reasoning cache flushed."

# Fault injection shortcuts (use SERVICE=auth-service to override)
SERVICE ?= payment-service
inject-cpu:
	.venv/bin/python3 backend/collector/fault_injector.py cpu_spike --service $(SERVICE)

inject-memory:
	.venv/bin/python3 backend/collector/fault_injector.py memory_spike --service $(SERVICE)

inject-crash:
	.venv/bin/python3 backend/collector/fault_injector.py crash_loop --service $(SERVICE)
