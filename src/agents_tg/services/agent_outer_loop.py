"""Manus outer loop — max turns, checkpoint, replan wrapper."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.environment_context import AgentEnvironment

logger = logging.getLogger(__name__)

_CONTINUE_SUFFIX = "[[CONTINUE]]"


class AgentOuterLoop:
    """Wrap agent dispatch with turn limits and checkpoint persistence."""

    async def run(
        self,
        *,
        agent_key: str,
        user_text: str,
        user_id: str = "default",
        environment: AgentEnvironment | None = None,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> Optional[str]:
        settings = get_settings()
        max_turns = max(1, settings.MAX_AGENT_TURNS)
        current_text = user_text
        result: Optional[str] = None

        for turn in range(max_turns):
            result = await self._dispatch_once(
                agent_key=agent_key,
                user_text=current_text,
                user_id=user_id,
                environment=environment,
            )

            if task_id:
                from src.agents_tg.services.plan_executor import plan_executor

                await plan_executor.save_checkpoint(
                    task_id,
                    {
                        "last_result": (result or "")[:1000],
                        "agent_key": agent_key,
                        "turn": turn + 1,
                        "status": "running",
                    },
                )

            if result is None:
                break

            stripped = result.strip()
            if stripped.upper() in ("NO_REPLY", "SILENT_REPLY"):
                return result

            if stripped.endswith(_CONTINUE_SUFFIX):
                partial = stripped[: -len(_CONTINUE_SUFFIX)].strip()
                current_text = (
                    f"{user_text}\n\n[Промежуточный результат, turn {turn + 1}]: "
                    f"{partial}"
                )
                continue

            break

        return result

    async def run_with_runner(
        self,
        *,
        agent_key: str,
        soul: str,
        user_message: str,
        user_id: str = "default",
        task_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Wrap agent_runner for specialists using soul-based loop."""
        from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
        from src.agents_tg.services.agent_runner import agent_runner

        settings = get_settings()
        profile = get_delivery_profile(agent_key)
        effective_max = min(settings.MAX_AGENT_TURNS, profile.max_tool_rounds * 4)
        effective_max = max(effective_max, profile.max_tool_rounds)

        result = await agent_runner.run(
            agent_key=agent_key,
            soul=soul,
            user_message=user_message,
            user_id=user_id,
            max_tool_rounds_override=effective_max,
            **kwargs,
        )

        if task_id:
            from src.agents_tg.services.plan_executor import plan_executor

            await plan_executor.save_checkpoint(
                task_id,
                {"last_result": result[:1000], "turns": effective_max},
            )
        return result

    async def _dispatch_once(
        self,
        *,
        agent_key: str,
        user_text: str,
        user_id: str,
        environment: AgentEnvironment | None,
    ) -> Optional[str]:
        env_block = environment.to_prompt_block() if environment else ""

        if agent_key == "orchestrator":
            from src.agents_tg.agents.orchestrator import orchestrator

            return await orchestrator.process(
                user_text,
                user_id=user_id,
                environment=environment,
            )
        if agent_key == "personal_assistant":
            from src.agents_tg.agents.personal_assistant import personal_assistant

            return await personal_assistant.process(
                user_text,
                user_id=user_id,
                environment=environment,
            )

        from src.agents_tg.agents.specialists import (
            business_manager,
            coder,
            marketing,
            research_analyst,
            security_ai,
        )

        agent_map = {
            "coder": coder,
            "research": research_analyst,
            "security_ai": security_ai,
            "business_manager": business_manager,
            "marketing": marketing,
        }
        agent = agent_map.get(agent_key)
        if agent:
            return await agent.process(
                user_text,
                user_id=user_id,
                environment=environment,
                environment_block=env_block,
            )
        return None


agent_outer_loop = AgentOuterLoop()
