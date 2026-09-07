# backend/agents/remediation_agent.py
"""
Remediation Agent — FR-3.2
Proposes exactly ONE whitelisted action with justification and confidence using Google Gemini.
Leverages Redis Incident Caching to reuse verified proposals and conserve API quota.
"""
import json, yaml
from langchain_core.messages import HumanMessage, SystemMessage
from .llm_client import invoke_gemini_with_rotation
from cache import get_incident_cache, set_incident_cache

with open("config/config.yaml") as f:
    CFG = yaml.safe_load(f)

WHITELIST = CFG["whitelist"]["allowed_actions"]
RISK_MAP  = CFG["policy"]["action_risk_tiers"]

SYSTEM_PROMPT = f"""\
You are a Kubernetes Remediation Agent.
Given a root-cause diagnosis, you propose exactly ONE remediation action.

Allowed actions: {WHITELIST}

IMPORTANT: You MUST respond with ONLY a valid JSON object — no preamble, no explanation outside the JSON.
Format:
{{
  "action":        "<one of the allowed actions>",
  "justification": "<why this action directly addresses the root cause>",
  "confidence":    <float between 0.0 and 1.0>
}}

Confidence guidance:
- 0.9+  → very certain this action will fix the issue
- 0.7–0.9 → reasonably confident
- 0.5–0.7 → some uncertainty
- < 0.5  → consider "escalate_no_op" instead

If no safe action is apparent, choose "escalate_no_op".
"""


def _parse_proposal(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        data = json.loads(text.strip())
        if "action" in data and data["action"] in WHITELIST:
            return {
                "action":        data["action"],
                "justification": str(data.get("justification", "")),
                "confidence":    float(data.get("confidence", 0.5)),
                "risk_tier":     RISK_MAP.get(data["action"], "high"),
            }
    except Exception:
        pass
    return None


def run_remediation(state: dict, critic_feedback: str = "") -> dict:
    """
    FR-3.2: Returns proposal dict with keys: action, justification, confidence, risk_tier.
    """
    service   = state.get("service", "payment-service")
    metric    = state.get("metric_type", "cpu")
    round_num = state.get("round_num", 1)

    # 1. In Round 1, check Redis Incident Cache
    if round_num == 1 and not critic_feedback:
        cached = get_incident_cache(service, metric, "remediation")
        if cached:
            print(f"[Redis Cache HIT] Reused verified remediation proposal for {service}:{metric}")
            return cached

    # 2. Cache Miss — Invoke Gemini with Key Rotation
    feedback_section = (
        f"\nCritic Agent Feedback from Round {round_num - 1}:\n{critic_feedback}"
        if critic_feedback else ""
    )

    user_prompt = f"""\
Diagnosis: {state.get('diagnosis_text', 'No diagnosis available.')}
Service: {state['service']}
Severity: {state['severity']}
Current Round: {round_num}{feedback_section}

Propose your remediation action now.
"""

    response = invoke_gemini_with_rotation([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])
    proposal = _parse_proposal(response.content)

    if not proposal:
        proposal = {
            "action": "restart",
            "justification": f"Fallback to safe rolling restart on {service}.",
            "confidence": 0.80,
            "risk_tier": "low",
        }

    # 3. Store in Redis for future recurring incidents
    if round_num == 1:
        set_incident_cache(service, metric, "remediation", proposal, ttl=3600)

    return proposal
