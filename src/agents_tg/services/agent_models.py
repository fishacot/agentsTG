"""Per-agent Hugging Face model selection (free Inference API tier).

Models must be available in your HF Inference Providers settings.
Qwen family is used by default for maximum compatibility on free tier.
Override any model via env: MODEL_<AGENT_KEY> (see settings.py).
"""

from typing import Final

# Shared general model — confirmed working on HF Inference Providers
MODEL_QWEN_7B: Final[str] = "Qwen/Qwen2.5-7B-Instruct"

# Orchestrator: JSON planning, routing, multi-step coordination
MODEL_ORCHESTRATOR: Final[str] = MODEL_QWEN_7B

# Personal assistant: structured action parsing (notes, tasks)
MODEL_PERSONAL_ASSISTANT: Final[str] = MODEL_QWEN_7B

# Coder: code generation, architecture, review
MODEL_CODER: Final[str] = "Qwen/Qwen2.5-Coder-7B-Instruct"

# Research: synthesis, summaries with sources
MODEL_RESEARCH: Final[str] = MODEL_QWEN_7B

# Security: analytical reasoning, structured risk reports
MODEL_SECURITY: Final[str] = MODEL_QWEN_7B

# Business: structured plans, MVP, prioritization
MODEL_BUSINESS: Final[str] = MODEL_QWEN_7B

# Marketing: creative copy, positioning, content plans
MODEL_MARKETING: Final[str] = MODEL_QWEN_7B

# General fallback
MODEL_DEFAULT: Final[str] = MODEL_QWEN_7B

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
