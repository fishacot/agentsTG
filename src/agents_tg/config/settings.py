"""Application configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Convert Render/Heroku/Neon postgres URL to async SQLAlchemy driver."""
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    if not parsed.query:
        return url

    qs = parse_qs(parsed.query, keep_blank_values=True)
    # Neon may append channel_binding=require — asyncpg rejects this kwarg.
    qs.pop("channel_binding", None)
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


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

    # Private channel for Elza notes (bot must be channel admin)
    NOTES_CHANNEL_ID: int = 0

    # AI — multi-provider (see LLM_PROVIDER_CHAIN)
    GROQ_API_KEY: str = ""
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Comma-separated fallback order, e.g. gemini,groq,huggingface
    LLM_PROVIDER_CHAIN: str = "gemini,groq"

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
    APP_TIMEZONE: str = "Europe/Moscow"
    HEALTH_PORT: int = 8080
    MESSAGE_DEBOUNCE_MS: int = 2000
    LLM_COOLDOWN_SEC: float = 3.0

    # Proactive agent wake (OpenClaw heartbeat parity)
    HEARTBEAT_ENABLED: bool = True
    HEARTBEAT_INTERVAL_MIN: int = 30
    HEARTBEAT_QUIET_HOURS: float = 12.0
    HEARTBEAT_SKIP_IF_BUSY_MIN: int = 5
    HEARTBEAT_DIGEST_LLM: bool = True
    HEARTBEAT_ACTIVE_HOURS_START: int = 8
    HEARTBEAT_ACTIVE_HOURS_END: int = 23
    HEARTBEAT_LIGHT_CONTEXT: bool = True
    HEARTBEAT_SKIP_WHEN_BUSY: bool = True

    # Cron reminders → full AgentRun (LLM delivery); static fallback on failure
    REMINDER_LLM_DELIVERY: bool = True

    # Manus-style confirmation gates for destructive actions
    REQUIRE_CONFIRM: bool = False

    # Manus outer loop
    MAX_AGENT_TURNS: int = 15

    # Progress UX
    HUMAN_DELAY_MS_MIN: int = 800
    HUMAN_DELAY_MS_MAX: int = 2500
    SHOW_AGENT_THOUGHT: bool = False

    # Sandbox (L4)
    SANDBOX_ENABLED: bool = True
    SANDBOX_REQUIRED: bool = True

    # Plugin allow/deny (OpenClaw parity)
    PLUGIN_ALLOW_LIST: str = ""
    PLUGIN_DENY_LIST: str = ""

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
    def llm_provider_chain_list(self) -> list[str]:
        raw = (self.LLM_PROVIDER_CHAIN or "").strip()
        if not raw:
            return []
        return [p.strip().lower() for p in raw.split(",") if p.strip()]

    @property
    def llm_api_key(self) -> str:
        """Legacy: first available API key."""
        return self.GEMINI_API_KEY or self.GROQ_API_KEY or self.QWEN_API_KEY

    @property
    def llm_api_base(self) -> str:
        if self.GEMINI_API_KEY:
            return f"{self.GEMINI_API_BASE.rstrip('/')}/chat/completions"
        if self.GROQ_API_KEY:
            return self.GROQ_API_BASE
        return self.QWEN_API_BASE

    @property
    def llm_default_model(self) -> str:
        if self.GEMINI_API_KEY:
            return self.GEMINI_MODEL
        if self.GROQ_API_KEY:
            return self.GROQ_MODEL
        return self.QWEN_MODEL

    def get_agent_model_override(self, agent_key: str) -> str:
        """Env MODEL_* override only (empty if not set)."""
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
        return (env_map.get(agent_key) or "").strip()

    def get_agent_model(self, agent_key: str, provider: str | None = None) -> str:
        """Resolve model id (env override → provider matrix)."""
        from src.agents_tg.services.agent_models import get_model_for_provider

        override = self.get_agent_model_override(agent_key)
        if override:
            return override
        prov = provider or (
            self.llm_provider_chain_list[0] if self.llm_provider_chain_list else "groq"
        )
        return get_model_for_provider(agent_key, prov)


def get_settings() -> AppSettings:
    """Return singleton settings instance."""
    return AppSettings()  # noqa: FURB113
