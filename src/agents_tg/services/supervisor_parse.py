"""Parse supervisor LLM output (JSON v2 + legacy routing or HTML fallback)."""

from __future__ import annotations

import json
from typing import Any

from src.agents_tg.services.prompts.orchestrator_directives import AGENT_NAME_ALIASES


def _normalize_agent_name(name: str) -> str:
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    return AGENT_NAME_ALIASES.get(key, key or "general")


def normalize_supervisor_data(data: dict[str, Any]) -> dict[str, Any]:
    """Map v2 action_type schema to internal next_agent / direct_reply / plan."""
    action = (data.get("action_type") or "").strip().lower()
    reasoning = (data.get("reasoning") or data.get("thought") or "").strip()
    plan = data.get("plan") or []
    if not isinstance(plan, list):
        plan = []

    if action:
        if action == "delegate":
            agent = _normalize_agent_name(str(data.get("agent_name", "general")))
            task = (data.get("task_description") or "").strip()
            return {
                "next_agent": agent,
                "direct_reply": "",
                "plan": plan or ([task] if task else []),
                "thought": reasoning,
                "action_type": action,
                "request_replan": False,
            }
        if action == "final_answer":
            answer = (data.get("final_answer") or "").strip()
            return {
                "next_agent": "end",
                "direct_reply": answer,
                "plan": plan,
                "thought": reasoning,
                "action_type": action,
                "request_replan": False,
            }
        if action == "direct_reply":
            msg = (data.get("user_message") or data.get("direct_reply") or "").strip()
            return {
                "next_agent": "end",
                "direct_reply": msg,
                "plan": plan,
                "thought": reasoning,
                "action_type": action,
                "request_replan": False,
            }
        if action == "request_replan":
            return {
                "next_agent": "general",
                "direct_reply": "",
                "plan": [],
                "thought": reasoning,
                "action_type": action,
                "request_replan": True,
            }

    next_agent = _normalize_agent_name(str(data.get("next_agent", "general")))
    direct_reply = (data.get("direct_reply") or "").strip()
    return {
        "next_agent": next_agent,
        "direct_reply": direct_reply,
        "plan": plan,
        "thought": reasoning or (data.get("thought") or "").strip(),
        "action_type": action or "legacy",
        "request_replan": False,
    }


def parse_supervisor_response(raw: str) -> dict[str, Any]:
    """Parse JSON routing or fallback to direct HTML reply."""
    clean = (raw or "").strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif clean.startswith("```"):
        parts = clean.split("```")
        if len(parts) >= 2:
            clean = parts[1].strip()

    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return normalize_supervisor_data(data)
    except json.JSONDecodeError:
        pass

    if clean and not clean.lstrip().startswith("{"):
        return normalize_supervisor_data(
            {
                "action_type": "direct_reply",
                "user_message": clean,
                "reasoning": "plain_text_fallback",
            }
        )
    raise ValueError(f"Invalid supervisor JSON: {raw[:200]}")
