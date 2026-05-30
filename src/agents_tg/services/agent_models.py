"""Per-agent model selection per LLM provider (free tier)."""

from typing import Final

# Groq
MODEL_LLAMA_8B: Final[str] = "llama-3.1-8b-instant"
MODEL_LLAMA_70B: Final[str] = "llama-3.3-70b-versatile"
MODEL_QWEN3_32B: Final[str] = "qwen/qwen3-32b"

# Gemini (OpenAI-compatible id)
MODEL_GEMINI_FLASH: Final[str] = "gemini-2.5-flash"
MODEL_GEMINI_FLASH_LITE: Final[str] = "gemini-2.5-flash-lite"

# Hugging Face legacy
MODEL_HF_DEFAULT: Final[str] = "Qwen/Qwen2.5-7B-Instruct"

# Defaults: orchestrator uses 8B for routing (lower TPM); override via MODEL_ORCHESTRATOR env
MODEL_ORCHESTRATOR: Final[str] = MODEL_LLAMA_8B
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

PROVIDER_MODELS: Final[dict[str, dict[str, str]]] = {
    "groq": {
        "orchestrator": MODEL_LLAMA_8B,
        "personal_assistant": MODEL_LLAMA_8B,
        "coder": MODEL_QWEN3_32B,
        "research": MODEL_LLAMA_8B,
        "security_ai": MODEL_LLAMA_8B,
        "business_manager": MODEL_LLAMA_8B,
        "marketing": MODEL_LLAMA_8B,
        "general": MODEL_LLAMA_8B,
    },
    "gemini": {
        "orchestrator": MODEL_GEMINI_FLASH_LITE,
        "personal_assistant": MODEL_GEMINI_FLASH,
        "coder": MODEL_GEMINI_FLASH,
        "research": MODEL_GEMINI_FLASH,
        "security_ai": MODEL_GEMINI_FLASH_LITE,
        "business_manager": MODEL_GEMINI_FLASH_LITE,
        "marketing": MODEL_GEMINI_FLASH,
        "general": MODEL_GEMINI_FLASH_LITE,
    },
    "huggingface": {
        "orchestrator": MODEL_HF_DEFAULT,
        "personal_assistant": "microsoft/Phi-3.5-mini-instruct",
        "coder": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "research": MODEL_HF_DEFAULT,
        "security_ai": "mistralai/Mistral-7B-Instruct-v0.3",
        "business_manager": MODEL_HF_DEFAULT,
        "marketing": "mistralai/Mistral-7B-Instruct-v0.3",
        "general": MODEL_HF_DEFAULT,
    },
}


def get_model_for_provider(agent_key: str, provider: str) -> str:
    """Resolve model id for agent + provider."""
    provider_map = PROVIDER_MODELS.get(provider, {})
    return provider_map.get(agent_key, provider_map.get("general", MODEL_DEFAULT))
