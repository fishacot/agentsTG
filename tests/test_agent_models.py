"""Tests for per-agent Hugging Face model configuration."""

from src.agents_tg.config.settings import AppSettings
from src.agents_tg.services.agent_models import (
    AGENT_MODELS,
    MODEL_CODER,
    MODEL_ORCHESTRATOR,
    MODEL_PERSONAL_ASSISTANT,
)


class TestAgentModels:
    """Verify model mapping for each agent role."""

    def test_all_seven_agents_have_models(self):
        expected_keys = {
            "orchestrator",
            "personal_assistant",
            "coder",
            "research",
            "security_ai",
            "business_manager",
            "marketing",
        }
        assert expected_keys.issubset(AGENT_MODELS.keys())

    def test_coder_uses_qwen_on_groq(self):
        assert "qwen" in MODEL_CODER.lower()

    def test_coder_differs_from_general(self):
        assert MODEL_CODER != MODEL_ORCHESTRATOR

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MODEL_CODER", "custom/coder-model")
        settings = AppSettings()
        assert settings.get_agent_model("coder") == "custom/coder-model"

    def test_default_fallback_for_unknown_agent(self):
        settings = AppSettings()
        model = settings.get_agent_model("unknown_agent")
        assert model == AGENT_MODELS["general"]
