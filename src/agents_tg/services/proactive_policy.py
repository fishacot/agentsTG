"""Per-agent proactive behavior (heartbeat, digest, cron)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProactivePolicy:
    heartbeat: bool = False
    morning_digest: bool = False
    cron_reminders: bool = False
    project_checkin: bool = False


POLICIES: dict[str, ProactivePolicy] = {
    "personal_assistant": ProactivePolicy(
        heartbeat=True,
        morning_digest=True,
        cron_reminders=True,
    ),
    "orchestrator": ProactivePolicy(project_checkin=True),
    "research": ProactivePolicy(),
    "coder": ProactivePolicy(),
    "security_ai": ProactivePolicy(),
    "business_manager": ProactivePolicy(),
    "marketing": ProactivePolicy(),
}


def get_proactive_policy(agent_key: str) -> ProactivePolicy:
    return POLICIES.get(agent_key, ProactivePolicy())


def allows_heartbeat(agent_key: str) -> bool:
    return get_proactive_policy(agent_key).heartbeat


def allows_project_checkin(agent_key: str) -> bool:
    return get_proactive_policy(agent_key).project_checkin
