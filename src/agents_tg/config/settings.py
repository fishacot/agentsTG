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

    # AI Settings
    QWEN_API_KEY: str = ""
    QWEN_API_BASE: str = (
        "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct"
    )
    QWEN_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"

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


def get_settings() -> AppSettings:
    """Return singleton settings instance."""
    return AppSettings()  # noqa: FURB113
