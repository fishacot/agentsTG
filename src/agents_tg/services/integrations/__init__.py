"""External service integrations (calendar, GitHub, …)."""

from src.agents_tg.services.integrations.base import IntegrationError, audit_integration
from src.agents_tg.services.integrations.calendar import create_calendar_event
from src.agents_tg.services.integrations.github import list_github_issues

__all__ = [
    "IntegrationError",
    "audit_integration",
    "create_calendar_event",
    "list_github_issues",
]
