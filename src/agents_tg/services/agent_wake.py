"""Proactive agent wake: heartbeat, LLM morning digest, event delivery."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_runtime import TriggerKind, agent_runtime
from src.agents_tg.services.user_contact_service import user_contact_service
from src.agents_tg.services.workspace_memory import load_heartbeat_md

logger = logging.getLogger(__name__)

SendFn = Callable[[int, int, str, str], Awaitable[None]]
ProcessFn = Callable[..., Awaitable[str | None]]


class AgentWakeService:
    """Background scheduler for proactive LLM turns (OpenClaw heartbeat parity)."""

    def __init__(self) -> None:
        self._loop_task: asyncio.Task | None = None
        self._send_fn: SendFn | None = None
        self._process_fn: ProcessFn | None = None

    def set_send_fn(self, fn: SendFn) -> None:
        self._send_fn = fn

    def set_process_fn(self, fn: ProcessFn) -> None:
        self._process_fn = fn

    async def start(self) -> None:
        settings = get_settings()
        if not settings.HEARTBEAT_ENABLED:
            logger.info("AgentWakeService disabled (HEARTBEAT_ENABLED=false)")
            return
        if self._loop_task and not self._loop_task.done():
            return
        self._loop_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "AgentWakeService started (interval=%s min, quiet=%sh)",
            settings.HEARTBEAT_INTERVAL_MIN,
            settings.HEARTBEAT_QUIET_HOURS,
        )

    async def stop(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self) -> None:
        settings = get_settings()
        interval = max(5, settings.HEARTBEAT_INTERVAL_MIN) * 60
        while True:
            try:
                await self.run_heartbeat_pass()
            except Exception as exc:
                logger.exception("Heartbeat pass error: %s", exc)
            await asyncio.sleep(interval)

    async def run_heartbeat_pass(self) -> None:
        settings = get_settings()
        if not settings.HEARTBEAT_ENABLED:
            return

        quiet = timedelta(hours=settings.HEARTBEAT_QUIET_HOURS)
        busy = timedelta(minutes=settings.HEARTBEAT_SKIP_IF_BUSY_MIN)
        now = datetime.now(timezone.utc)

        candidates = await user_contact_service.list_wake_candidates(
            agent_key="personal_assistant"
        )
        for row in candidates:
            last_in = self._as_utc(row.get("last_inbound_at"))
            if not last_in:
                continue
            if now - last_in < busy:
                continue
            if now - last_in < quiet:
                continue

            last_hb = self._as_utc(row.get("last_heartbeat_at"))
            if last_hb and now - last_hb < quiet:
                continue

            tg_uid = int(row["telegram_user_id"])
            chat_id = int(row["chat_id"])
            hours_silent = round((now - last_in).total_seconds() / 3600, 1)
            heartbeat_md = load_heartbeat_md(tg_uid)
            prompt = (
                f"[Проактивный heartbeat — пользователь молчит ~{hours_silent} ч.]\n"
                "Выполни чеклист HEARTBEAT. Если нечего сказать — ответь ровно HEARTBEAT_OK.\n\n"
                f"## HEARTBEAT.md\n{heartbeat_md}"
            )
            await self._run_and_deliver(
                agent_key="personal_assistant",
                telegram_user_id=tg_uid,
                chat_id=chat_id,
                prompt=prompt,
                trigger=TriggerKind.CRON,
                record_heartbeat=True,
            )

    async def run_morning_digest(self, chat_id: int, telegram_user_id: int) -> None:
        settings = get_settings()
        if not settings.HEARTBEAT_DIGEST_LLM:
            body = (
                "🌅 Доброе утро! Напишите «мои дела» или «план на день» — помогу разложить."
            )
            await self._send_plain(chat_id, telegram_user_id, body)
            return

        from src.agents_tg.services.reminder_service import reminder_service
        from src.agents_tg.services.user_tasks_service import user_tasks_service

        tasks = await user_tasks_service.list_tasks(telegram_user_id=telegram_user_id)
        pending = await reminder_service.list_pending(telegram_user_id)
        task_lines = ", ".join(t["title"] for t in tasks.get("tasks") or []) or "нет"
        rem_lines = ", ".join(
            (p.get("text") or "")[:40] for p in pending[:5]
        ) or "нет"

        prompt = (
            "[Утренний digest 09:00 МСК — проактивное сообщение]\n"
            "Составь короткое тёплое приветствие и план дня: задачи, проект из ФОКУС, "
            "напоминания. 2–4 предложения, без markdown-заголовков.\n\n"
            f"- Открытые задачи: {task_lines}\n"
            f"- Напоминания: {rem_lines}\n"
        )
        await self._run_and_deliver(
            agent_key="personal_assistant",
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            prompt=prompt,
            trigger=TriggerKind.CRON,
            record_heartbeat=False,
            prefix="🌅 ",
        )

    async def run_event_wake(
        self,
        *,
        agent_key: str,
        telegram_user_id: int,
        chat_id: int,
        prompt: str,
        trigger: TriggerKind = TriggerKind.BACKGROUND,
    ) -> None:
        """Deliver proactive message after background job or delegation completes."""
        await self._run_and_deliver(
            agent_key=agent_key,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            prompt=prompt,
            trigger=trigger,
            record_heartbeat=False,
        )

    async def _run_and_deliver(
        self,
        *,
        agent_key: str,
        telegram_user_id: int,
        chat_id: int,
        prompt: str,
        trigger: TriggerKind,
        record_heartbeat: bool,
        prefix: str = "",
    ) -> None:
        if not self._process_fn:
            logger.warning("AgentWake: no process_fn configured")
            return

        result = await agent_runtime.run_scheduled(
            agent_key=agent_key,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            user_text=prompt,
            trigger=trigger,
            process_fn=self._process_fn,
        )

        if result.silent or not result.messages:
            if record_heartbeat:
                await user_contact_service.record_heartbeat(
                    telegram_user_id=telegram_user_id,
                    agent_key=agent_key,
                )
            return

        body = prefix + result.messages[0]
        await self._send_plain(chat_id, telegram_user_id, body, agent_key)
        for extra in result.extras:
            await self._send_plain(chat_id, telegram_user_id, extra, agent_key)

        await user_contact_service.record_outbound(
            telegram_user_id=telegram_user_id,
            agent_key=agent_key,
        )
        if record_heartbeat:
            await user_contact_service.record_heartbeat(
                telegram_user_id=telegram_user_id,
                agent_key=agent_key,
            )

    async def _send_plain(
        self,
        chat_id: int,
        telegram_user_id: int,
        body: str,
        agent_key: str = "personal_assistant",
    ) -> None:
        if self._send_fn:
            try:
                await self._send_fn(chat_id, telegram_user_id, body, agent_key)
            except Exception as exc:
                logger.error("AgentWake delivery failed: %s", exc)
        else:
            logger.warning("AgentWake: no send_fn for chat %s", chat_id)

    @staticmethod
    def _as_utc(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        return None


agent_wake_service = AgentWakeService()
