"""Per-agent Hugging Face model selection (free Inference API tier).

Models are chosen for reliability on HF serverless inference and role fit.
Override any model via env: MODEL_<AGENT_KEY> (see settings.py).
"""

from typing import Final

# Orchestrator: JSON planning, routing, multi-step coordination
MODEL_ORCHESTRATOR: Final[str] = "Qwen/Qwen2.5-7B-Instruct"

# Personal assistant: fast structured action parsing (notes, tasks)
MODEL_PERSONAL_ASSISTANT: Final[str] = "microsoft/Phi-3.5-mini-instruct"

# Coder: code generation, architecture, review
MODEL_CODER: Final[str] = "Qwen/Qwen2.5-Coder-7B-Instruct"

# Research: long-context synthesis, summaries with sources
MODEL_RESEARCH: Final[str] = "meta-llama/Llama-3.1-8B-Instruct"

# Security: analytical reasoning, structured risk reports
MODEL_SECURITY: Final[str] = "mistralai/Mistral-7B-Instruct-v0.3"

# Business: structured plans, MVP, prioritization
MODEL_BUSINESS: Final[str] = "meta-llama/Llama-3.1-8B-Instruct"

# Marketing: creative copy, positioning, content plans
MODEL_MARKETING: Final[str] = "mistralai/Mistral-7B-Instruct-v0.3"

# General fallback
MODEL_DEFAULT: Final[str] = "Qwen/Qwen2.5-7B-Instruct"

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
