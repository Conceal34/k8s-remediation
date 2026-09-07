# backend/agents/diagnosis_agent.py
"""
Diagnosis Agent — FR-3.1
Produces a root-cause hypothesis using Google Gemini.
Leverages Redis Incident Caching to reuse verified diagnoses and conserve API quota.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from .llm_client import invoke_gemini_with_rotation
from cache import get_incident_cache, set_incident_cache

SYSTEM_PROMPT = """\
You are a Kubernetes infrastructure Diagnosis Agent.
Your role is to analyse anomaly data and produce a clear, specific root-cause hypothesis.

Rules you MUST follow:
- Describe WHAT is happening and WHY, using the metric values as evidence.
- Do NOT suggest any fix or remediation action — that is another agent's job.
- Keep your response to 2 to 4 sentences of plain prose.
- Be specific: name the service, the metric, and the likely cause.
- Do not use bullet points or numbered lists.
"""


def run_diagnosis(state: dict) -> str:
    """
    FR-3.1: Invokes Diagnosis Agent LLM with Redis Incident Caching.
    """
    service = state.get("service", "payment-service")
    metric  = state.get("metric_type", "cpu")

    # 1. Check Redis Incident Cache
    cached = get_incident_cache(service, metric, "diagnosis")
    if cached:
        print(f"[Redis Cache HIT] Reused verified diagnosis for {service}:{metric} (0 API calls used!)")
        return cached

    # 2. Cache Miss — Invoke Gemini with Key Rotation
    history_lines = "\n".join(
        f"  [{r.get('timestamp', '')}] {r.get('metric_type', '')}: {r.get('value', '')}"
        for r in state.get("recent_history", [])[:10]
    )

    user_prompt = f"""\
Service: {state['service']}
Anomaly Score: {state['anomaly_score']:.4f}
Severity: {state['severity']}
Triggering Metric: {state['metric_type']}

Recent metric history (last 10 samples across all metrics for this service):
{history_lines if history_lines else '  No history available.'}

Based on this data, provide your root-cause diagnosis.
"""

    response = invoke_gemini_with_rotation([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])
    diagnosis_text = response.content.strip()

    # 3. Store in Redis for future recurring incidents
    if diagnosis_text:
        set_incident_cache(service, metric, "diagnosis", diagnosis_text, ttl=3600)

    return diagnosis_text
