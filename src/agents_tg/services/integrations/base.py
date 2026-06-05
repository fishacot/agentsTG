"""Shared integration helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Raised when an external API call fails."""


def audit_integration(name: str, *, user_id: str, detail: str) -> None:
    try:
        from src.agents_tg.services.workspace_memory import append_journal_md

        append_journal_md(
            int(user_id) if user_id.isdigit() else 0,
            event_type="integration",
            summary=f"{name}: {detail[:200]}",
        )
    except Exception as exc:
        logger.debug("integration audit skipped: %s", exc)


def configured(*env_names: str) -> bool:
    from src.agents_tg.config.settings import get_settings

    settings = get_settings()
    for name in env_names:
        if getattr(settings, name, None):
            return True
    return False
