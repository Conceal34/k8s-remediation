"""
LLM Client Factory & Gemini Multi-Key Rotator with Ultimate Fallback.
Reads GEMINI_API_KEY / GEMINI_API_KEYS (supports multiple comma-separated keys).
Automatically rotates to the next API key if a 429 / ResourceExhausted error occurs.
Retries automatically on 503 / UNAVAILABLE errors with backoff.
Falls back to gemini-3.6-flash as the ultimate fallback model if the primary model fails.
"""
import os, yaml, time
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Ultimate fallback model constant
ULTIMATE_FALLBACK_MODEL = "gemini-3.6-flash"

try:
    with open("config/config.yaml") as f:
        CFG = yaml.safe_load(f)
except Exception:
    CFG = {}

# Collect all configured Gemini API keys (comma-separated or single)
_raw_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
API_KEYS = [k.strip() for k in _raw_env.split(",") if k.strip() and k.strip() != "your_gemini_api_key_here"]
if not API_KEYS:
    API_KEYS = ["dummy-key"]

_active_key_idx = 0


def get_active_key() -> str:
    """Returns the currently active Gemini API key."""
    global _active_key_idx
    return API_KEYS[_active_key_idx % len(API_KEYS)]


def rotate_to_next_key() -> str:
    """Rotates to the next Gemini API key in the pool."""
    global _active_key_idx
    _active_key_idx = (_active_key_idx + 1) % len(API_KEYS)
    new_key = API_KEYS[_active_key_idx]
    masked = new_key[:6] + "..." + new_key[-4:] if len(new_key) > 10 else "***"
    print(f"[Gemini Key Rotation] 🔄 Rotated to key {_active_key_idx + 1}/{len(API_KEYS)} ({masked})")
    return new_key


def get_llm(model_override: str | None = None, key_override: str | None = None) -> BaseChatModel:
    """Returns a configured Gemini LangChain model instance with fallback to gemini-3.6-flash."""
    model = model_override or CFG.get("agents", {}).get("model", {}).get("gemini", ULTIMATE_FALLBACK_MODEL)
    temp  = CFG.get("agents", {}).get("temperature", 0.2)
    key   = key_override or get_active_key()

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temp,
        google_api_key=key,
        convert_system_message_to_human=True,
        max_retries=3,
    )


def _try_invoke_model_across_keys(messages: list, target_model: str, temperature: float = 0.2):
    """Attempts to invoke a specific model across all available API keys, with internal retry for 503s."""
    last_exc = None

    for attempt in range(len(API_KEYS)):
        current_key = get_active_key()
        
        # We will try up to 3 times per key for transient server errors (503/500/502)
        for retry in range(3):
            try:
                llm = ChatGoogleGenerativeAI(
                    model=target_model,
                    temperature=temperature,
                    google_api_key=current_key,
                    convert_system_message_to_human=True,
                    max_retries=3,
                )
                return llm.invoke(messages)
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                
                # Transient Server Errors -> Wait and retry same key
                if "503" in exc_str or "unavailable" in exc_str or "500" in exc_str or "502" in exc_str or "504" in exc_str:
                    wait_time = 2 ** retry  # Exponential backoff: 1s, 2s, 4s...
                    print(f"[Gemini Retry] ⏳ Transient API error (503/UNAVAILABLE). Retrying {retry+1}/3 in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Quota / Rate Limit / Not Found -> Rotate key if possible
                if "429" in exc_str or "quota" in exc_str or "resourceexhausted" in exc_str or "notfound" in exc_str or "404" in exc_str:
                    if len(API_KEYS) > 1 and attempt < len(API_KEYS) - 1:
                        rotate_to_next_key()
                        break # Break inner retry loop to try next key in outer loop
                
                # Fatal error (e.g. 400 Bad Request) -> Raise immediately
                raise exc
        else:
            # If we exhausted all 3 retries for transient errors and still failed
            if attempt >= len(API_KEYS) - 1:
                raise last_exc
            rotate_to_next_key()

    raise last_exc


def invoke_gemini_with_rotation(messages: list, model: str | None = None, temperature: float = 0.2):
    """
    Invokes Gemini with automatic multi-key rotation, 503 retry, and ultimate fallback to gemini-3.6-flash.
    1. First tries configured/requested model across all API keys.
    2. If that fails and target_model != ULTIMATE_FALLBACK_MODEL, tries ULTIMATE_FALLBACK_MODEL across all keys.
    """
    primary_model = model or CFG.get("agents", {}).get("model", {}).get("gemini", ULTIMATE_FALLBACK_MODEL)

    try:
        return _try_invoke_model_across_keys(messages, primary_model, temperature)
    except Exception as primary_exc:
        if primary_model != ULTIMATE_FALLBACK_MODEL:
            print(f"[Gemini Fallback] ⚠️ Primary model '{primary_model}' failed ({primary_exc}). Falling back to ultimate model '{ULTIMATE_FALLBACK_MODEL}'...")
            try:
                return _try_invoke_model_across_keys(messages, ULTIMATE_FALLBACK_MODEL, temperature)
            except Exception as fallback_exc:
                print(f"[Gemini Fallback] ⚠️ Ultimate fallback model '{ULTIMATE_FALLBACK_MODEL}' also failed: {fallback_exc}")
                raise fallback_exc
        raise primary_exc
