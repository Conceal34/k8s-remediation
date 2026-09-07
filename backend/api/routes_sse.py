"""
Server-Sent Events endpoint — streams real-time pipeline events to the frontend.
No polling: the browser opens one persistent HTTP connection and receives push events.
"""
import asyncio, json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agents.pipeline import sse_subscribe, sse_unsubscribe

router = APIRouter()

@router.get("/pipeline-feed")
async def pipeline_feed():
    """
    SSE endpoint.  Each event is JSON, prefixed with 'data: ' per the SSE spec.
    Event types: anomaly_detected | diagnosis | remediation | critic | outcome | error
    """
    q = sse_subscribe()

    async def event_stream():
        # Send an initial heartbeat so the browser knows the connection is live
        yield "data: {\"type\": \"connected\"}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send a keep-alive comment so proxies don't close the connection
                    yield ": keep-alive\n\n"
        finally:
            sse_unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables Nginx buffering
        },
    )
