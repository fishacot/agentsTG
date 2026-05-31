"""CLI: agent autonomy / infra status snapshot."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.agents_tg.config.settings import get_settings


async def _main() -> int:
    settings = get_settings()
    print("=== agentsTG agent status ===")
    print(f"HEARTBEAT_ENABLED: {settings.HEARTBEAT_ENABLED}")
    print(f"HEARTBEAT_INTERVAL_MIN: {settings.HEARTBEAT_INTERVAL_MIN}")
    print(f"HEARTBEAT_QUIET_HOURS: {settings.HEARTBEAT_QUIET_HOURS}")
    print(f"HEARTBEAT_DIGEST_LLM: {settings.HEARTBEAT_DIGEST_LLM}")
    print(f"DATABASE_URL set: {bool(settings.DATABASE_URL)}")

    try:
        from sqlalchemy import text

        from src.agents_tg.db.session import create_engine
        from src.agents_tg.services.user_contact_service import user_contact_service

        engine = create_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        user_contact_service.set_pg_engine(engine)
        contacts = await user_contact_service.list_wake_candidates(
            agent_key="personal_assistant"
        )
        print(f"PG: connected, wake contacts={len(contacts)}")
        await engine.dispose()
    except Exception as exc:
        print(f"PG: unavailable ({exc})")
        print("  → reminders/tasks/contacts use in-memory fallback")

    from src.agents_tg.services.agent_runtime import TriggerKind

    print(f"TriggerKind: {[t.value for t in TriggerKind]}")
    print("run_scheduled: implemented")
    print("AgentWakeService: implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
