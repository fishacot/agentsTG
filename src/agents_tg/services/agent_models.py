"""Per-agent Groq model selection (free tier, no credit card).

Override any model via env: MODEL_<AGENT_KEY> (see settings.py).
Docs: https://console.groq.com/docs/models
"""

from typing import Final

# Fast general model — high daily quota on Groq free tier
MODEL_LLAMA_8B: Final[str] = "llama-3.1-8b-instant"

# Stronger reasoning for orchestrator
MODEL_LLAMA_70B: Final[str] = "llama-3.3-70b-versatile"

# Qwen on Groq — coder and complex tasks
MODEL_QWEN3_32B: Final[str] = "qwen/qwen3-32b"

MODEL_ORCHESTRATOR: Final[str] = MODEL_LLAMA_70B
MODEL_PERSONAL_ASSISTANT: Final[str] = MODEL_LLAMA_8B
MODEL_CODER: Final[str] = MODEL_QWEN3_32B
MODEL_RESEARCH: Final[str] = MODEL_LLAMA_8B
MODEL_SECURITY: Final[str] = MODEL_LLAMA_8B
MODEL_BUSINESS: Final[str] = MODEL_LLAMA_8B
MODEL_MARKETING: Final[str] = MODEL_LLAMA_8B
MODEL_DEFAULT: Final[str] = MODEL_LLAMA_8B

AGENT_MODELS: Final[dict[str, str]] = {
    "orchestrator": MODEL_ORCHESTRATOR,
    "personal_assistant": MODEL_PERSONAL_ASSISTANT,
    "coder": MODEL_CODER,
    "research": MODEL_RESEARCH,
    "security_ai": MODEL_SECURITY,
    "business_manager": MODEL_BUSINESS,
    "marketing": MODEL_MARKETING,
    "general": MODEL_DEFAULT,
}
