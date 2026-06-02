"""Per-agent style prompt fragments."""

from src.agents_tg.services.prompts.styles.personal_assistant import MANUS_PA_STYLE
from src.agents_tg.services.prompts.styles.specialist import (
    MANUS_SPECIALIST_STYLE,
    WEB_TOOL_HINT,
)

__all__ = ["MANUS_PA_STYLE", "MANUS_SPECIALIST_STYLE", "WEB_TOOL_HINT"]
