"""Structured log helpers for observability."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("agents_tg.events")


def log_event(event: str, **fields: Any) -> None:
    """Emit a single-line JSON-ish log record for grep/aggregation."""
    payload = {"event": event, **fields}
    try:
        line = json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        line = str(payload)
    logger.info(line)
