"""Telegram HTML formatting and safe message sending (compat re-export)."""

from src.agents_tg.channels.telegram_delivery import (
    escape_html,
    sanitize_html_for_telegram,
    send_agent_response,
    split_telegram_html,
)

__all__ = [
    "escape_html",
    "sanitize_html_for_telegram",
    "send_agent_response",
    "split_telegram_html",
]
