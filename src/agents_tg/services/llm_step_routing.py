"""Optional per-step model overrides from STEP_MODEL_ROUTING JSON."""

from __future__ import annotations

import json
import logging

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)

_cached_table: dict[str, str] | None = None


def parse_step_model_routing(raw: str | None = None) -> dict[str, str]:
    """Parse settings JSON: {\"classify\":\"model-id\",\"finalize\":\"model-id\"}."""
    global _cached_table
    if raw is None:
        if _cached_table is not None:
            return _cached_table
        raw = get_settings().STEP_MODEL_ROUTING
    text = (raw or "").strip()
    if not text:
        _cached_table = {}
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("STEP_MODEL_ROUTING is not valid JSON")
        _cached_table = {}
        return {}
    if not isinstance(data, dict):
        _cached_table = {}
        return {}
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            out[key.strip().lower()] = value.strip()
    _cached_table = out
    return out


def resolve_step_model(
    step_kind: str | None,
    *,
    agent_key: str | None = None,
    default: str | None = None,
) -> str | None:
    """Return override model id for step_kind, or None to use agent default."""
    if not step_kind:
        return None
    table = parse_step_model_routing()
    kind = step_kind.strip().lower()
    if kind in table:
        return table[kind]
    if agent_key:
        agent_key = agent_key.strip().lower()
        composite = f"{agent_key}:{kind}"
        if composite in table:
            return table[composite]
    return default if default else None


def clear_routing_cache() -> None:
    """Test helper."""
    global _cached_table
    _cached_table = None
