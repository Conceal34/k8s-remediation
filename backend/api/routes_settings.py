from fastapi import APIRouter
import yaml

router = APIRouter()

@router.get("/")
def get_settings():
    """NFR-6.5: Expose current config values to the dashboard Settings view."""
    with open("config/config.yaml") as f:
        cfg = yaml.safe_load(f)
    # Return only UI-relevant settings (exclude secrets/internal paths)
    return {
        "polling_interval_seconds": cfg["cluster"]["polling_interval_seconds"],
        "anomaly_score_threshold":  cfg["anomaly_detection"]["anomaly_score_threshold"],
        "max_debate_rounds":        cfg["agents"]["max_debate_rounds"],
        "confidence_threshold":     cfg["policy"]["confidence_threshold"],
        "action_risk_tiers":        cfg["policy"]["action_risk_tiers"],
        "whitelist":                cfg["whitelist"]["allowed_actions"],
        "llm_model":                cfg["agents"]["model"]["gemini"],
    }
