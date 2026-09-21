"""
FastAPI application entry point.
Starts the DB, registers routes, and launches the metrics collection loop.
"""
import asyncio, yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from database.session  import create_tables
from agents.pipeline   import handle_anomaly
from api import routes_metrics, routes_decisions, routes_approvals, routes_settings, routes_sse, routes_chaos

with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    create_tables()
    # Inject the pipeline callback into the collector loop
    from collector.metrics_collector import collection_loop
    asyncio.create_task(collection_loop(anomaly_callback=handle_anomaly))
    yield
    # Shutdown: nothing to clean up for now


app = FastAPI(title="Agentic CloudOps API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CFG["api"]["cors_origins"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_metrics.router,   prefix="/api/metrics",   tags=["Metrics"])
app.include_router(routes_decisions.router, prefix="/api/decisions",  tags=["Decisions"])
app.include_router(routes_approvals.router, prefix="/api/approvals",  tags=["Approvals"])
app.include_router(routes_settings.router,  prefix="/api/settings",   tags=["Settings"])
app.include_router(routes_sse.router,       prefix="/api/sse",        tags=["SSE"])
app.include_router(routes_chaos.router,     prefix="/api/chaos",      tags=["Chaos Controls (Demo)"])

@app.get("/api/health")
def health():
    return {"status": "ok"}
