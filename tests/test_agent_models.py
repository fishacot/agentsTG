"""Tests for per-agent Hugging Face model configuration."""

from src.agents_tg.config.settings import AppSettings
from src.agents_tg.services.agent_models import (
    AGENT_MODELS,
    MODEL_CODER,
    MODEL_GEMINI_FLASH_LITE,
    MODEL_ORCHESTRATOR,
    get_model_for_provider,
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

    def test_orchestrator_uses_8b_not_70b(self):
        assert MODEL_ORCHESTRATOR == "llama-3.1-8b-instant"
        assert "70b" not in MODEL_ORCHESTRATOR.lower()

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MODEL_CODER", "custom/coder-model")
        settings = AppSettings()
        assert settings.get_agent_model("coder") == "custom/coder-model"

    def test_default_fallback_for_unknown_agent(self):
        settings = AppSettings()
        model = settings.get_agent_model("unknown_agent")
        expected = get_model_for_provider(
            "unknown_agent",
            settings.llm_provider_chain_list[0] or "groq",
        )
        assert model == expected

    def test_get_agent_model_gemini_chain(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER_CHAIN", "gemini,groq")
        settings = AppSettings()
        model = settings.get_agent_model("orchestrator")
        assert model == MODEL_GEMINI_FLASH_LITE
