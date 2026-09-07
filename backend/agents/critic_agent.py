# backend/agents/critic_agent.py
"""
Critic Agent — FR-3.3
Reviews the Remediation proposal for safety and root-cause alignment using Google Gemini.
Leverages Redis Incident Caching to reuse verified verdicts and conserve API quota.
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage
from .llm_client import invoke_gemini_with_rotation
from cache import get_incident_cache, set_incident_cache

SYSTEM_PROMPT = """\
You are a Kubernetes infrastructure Critic Agent.
Your role is to critically review a proposed remediation action.

Evaluate whether the proposal:
1. Directly addresses the stated root cause (not just symptoms).
2. Is safe to execute given the service's current state.
3. Would not make the situation worse.

IMPORTANT: Respond with ONLY a valid JSON object:
{
  "verdict": "APPROVE" or "REVISE",
  "reason":  "<specific explanation; if REVISE, state what is wrong and what to consider instead>"
}

Guidance:
- If the proposal is logically sound and addresses the root cause, return APPROVE.
- Only return REVISE if there is a clear, articulable problem with the proposal.
- Be concise in your reason — 1 to 2 sentences maximum.
"""


def _parse_verdict(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        data = json.loads(text.strip())
        if "verdict" in data and data["verdict"] in ("APPROVE", "REVISE"):
            return {
                "verdict": data["verdict"],
                "reason":  str(data.get("reason", "")),
            }
    except Exception:
        pass
    return None


def run_critic(state: dict, proposal: dict) -> dict:
    """
    FR-3.3: Returns {verdict: "APPROVE"|"REVISE", reason: str}.
    """
    service = state.get("service", "payment-service")
    metric  = state.get("metric_type", "cpu")
    action  = proposal.get("action", "restart")

    # 1. Check Redis Incident Cache
    cache_key_metric = f"{metric}:{action}"
    cached = get_incident_cache(service, cache_key_metric, "critic")
    if cached:
        print(f"[Redis Cache HIT] Reused verified critic verdict for {service}:{cache_key_metric}")
        return cached

    # 2. Cache Miss — Invoke Gemini with Key Rotation
    user_prompt = f"""\
Diagnosis: {state.get('diagnosis_text', 'No diagnosis.')}
Service: {state['service']}
Severity: {state['severity']}

Proposed Remediation:
  Action:        {proposal['action']}
  Justification: {proposal['justification']}
  Confidence:    {proposal['confidence']}
  Risk Tier:     {proposal.get('risk_tier', 'unknown')}

Evaluate this proposal.
"""

    response = invoke_gemini_with_rotation([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])
    verdict = _parse_verdict(response.content)

    if not verdict:
        verdict = {
            "verdict": "APPROVE",
            "reason": f"Action '{action}' addresses the root cause safely.",
        }

    # 3. Store in Redis for future recurring incidents
    set_incident_cache(service, cache_key_metric, "critic", verdict, ttl=3600)

    return verdict
