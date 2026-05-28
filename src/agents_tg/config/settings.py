"""Application configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Convert Render/Heroku postgres URL to async SQLAlchemy driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram - Multi-bot system (7 bots: 6 agents + orchestrator)
    BOT_TOKEN_ORCHESTRATOR: str = ""  # @orchestrator_agent
    BOT_TOKEN_PA: str = ""  # @pa_agent (Personal Assistant)
    BOT_TOKEN_CODER: str = ""  # @coder_agent
    BOT_TOKEN_RESEARCH: str = ""  # @research_agent
    BOT_TOKEN_SECURITY: str = ""  # @security_agent
    BOT_TOKEN_BUSINESS: str = ""  # @business_agent
    BOT_TOKEN_MARKETING: str = ""  # @marketing_agent

    # Legacy single bot (deprecated, kept for compatibility)
    BOT_TOKEN: str = ""

    # Group chat for inter-bot communication
    GROUP_CHAT_ID: int = 0  # ID of group where all bots collaborate

    # AI Settings — Groq (primary, free tier) or legacy Hugging Face fallback
    GROQ_API_KEY: str = ""
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    QWEN_API_KEY: str = ""
    QWEN_API_BASE: str = "https://router.huggingface.co/v1/chat/completions"
    QWEN_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"

    # Per-agent model overrides (optional; defaults in agent_models.py)
    MODEL_ORCHESTRATOR: str = ""
    MODEL_PERSONAL_ASSISTANT: str = ""
    MODEL_CODER: str = ""
    MODEL_RESEARCH: str = ""
    MODEL_SECURITY: str = ""
    MODEL_BUSINESS: str = ""
    MODEL_MARKETING: str = ""
    MODEL_DEFAULT: str = ""

    # Mem0 Settings
    MEM0_API_KEY: str = ""  # Optional if using local

    # Obsidian/Git Settings
    OBSIDIAN_VAULT_PATH: str = "vault"
    GIT_REMOTE_URL: str = ""  # URL of your private vault repo

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/agents_tg"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Paths
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

    @property
    def SRC_DIR(self) -> Path:
        return self.ROOT_DIR / "src"

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL with asyncpg driver for SQLAlchemy."""
        return normalize_database_url(self.DATABASE_URL)

    @property
    def llm_api_key(self) -> str:
        """Active LLM API key (Groq preferred)."""
        return self.GROQ_API_KEY or self.QWEN_API_KEY

    @property
    def llm_api_base(self) -> str:
        """Active LLM chat completions endpoint."""
        if self.GROQ_API_KEY:
            return self.GROQ_API_BASE
        return self.QWEN_API_BASE

    @property
    def llm_default_model(self) -> str:
        """Default model when none specified."""
        if self.GROQ_API_KEY:
            return self.GROQ_MODEL
        return self.QWEN_MODEL

    def get_agent_model(self, agent_key: str) -> str:
        """Resolve model id for an agent (env override → code default)."""
        from src.agents_tg.services.agent_models import AGENT_MODELS, MODEL_DEFAULT

        env_map = {
            "orchestrator": self.MODEL_ORCHESTRATOR,
            "personal_assistant": self.MODEL_PERSONAL_ASSISTANT,
            "coder": self.MODEL_CODER,
            "research": self.MODEL_RESEARCH,
            "security_ai": self.MODEL_SECURITY,
            "business_manager": self.MODEL_BUSINESS,
            "marketing": self.MODEL_MARKETING,
            "general": self.MODEL_DEFAULT,
        }
        override = env_map.get(agent_key, "")
        if override:
            return override
        return AGENT_MODELS.get(agent_key, MODEL_DEFAULT)


def get_settings() -> AppSettings:
    """Return singleton settings instance."""
    return AppSettings()  # noqa: FURB113
