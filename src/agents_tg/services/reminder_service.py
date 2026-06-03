"""Reminder scheduling and delivery (cron / one-shot, MSK)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from src.agents_tg.config.settings import get_settings
from src.agents_tg.utils.timezone_utils import format_local, local_to_utc

logger = logging.getLogger(__name__)

MORNING_DIGEST_MARKER = "__morning_digest__"
MORNING_DIGEST_TEXT = (
    "Доброе утро! Напишите «мои дела» или «план на день» — помогу разложить."
)

SendFn = Callable[[int, int, str, str], Awaitable[None]]
DigestFn = Callable[[int, int], Awaitable[None]]
CronDeliverFn = Callable[[int, int, str, str], Awaitable[None]]


@dataclass
class _MemoryReminder:
    id: int
    telegram_user_id: int
    chat_id: int
    agent_key: str
    text: str
    fire_at: datetime
    recurrence: str = "once"
    status: str = "pending"


class ReminderService:
    """Schedule and fire Telegram reminders."""

    def __init__(self) -> None:
        self._memory: list[_MemoryReminder] = []
        self._next_id = 1
        self._scheduler: Any | None = None
        self._send_fn: SendFn | None = None
        self._digest_fn: DigestFn | None = None
        self._cron_deliver_fn: CronDeliverFn | None = None
        self._pg_engine: Any | None = None
        self._poll_task: asyncio.Task | None = None

    def set_pg_engine(self, engine: Any) -> None:
        self._pg_engine = engine

    def set_send_fn(self, fn: SendFn) -> None:
        self._send_fn = fn

    def set_digest_fn(self, fn: DigestFn) -> None:
        self._digest_fn = fn

    def set_cron_deliver_fn(self, fn: CronDeliverFn) -> None:
        self._cron_deliver_fn = fn

    async def schedule(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        text: str,
        fire_at_local: datetime,
        agent_key: str = "personal_assistant",
        is_digest: bool = False,
        recurrence: str = "once",
    ) -> dict[str, Any]:
        if is_digest:
            text = MORNING_DIGEST_MARKER + text
            recurrence = "daily"
        fire_at_utc = local_to_utc(fire_at_local)
        tz_name = get_settings().APP_TIMEZONE
        recurrence = (recurrence or "once").lower()
        if recurrence not in ("once", "daily"):
            recurrence = "once"

        if self._pg_engine:
            rid = await self._insert_pg(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                text=text,
                fire_at=fire_at_utc,
                agent_key=agent_key,
                tz_name=tz_name,
                recurrence=recurrence,
            )
        else:
            rid = self._next_id
            self._next_id += 1
            self._memory.append(
                _MemoryReminder(
                    id=rid,
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    agent_key=agent_key,
                    text=text,
                    fire_at=fire_at_utc,
                    recurrence=recurrence,
                )
            )

        logger.info(
            "Scheduled reminder id=%s at %s for user=%s",
            rid,
            format_local(fire_at_local),
            telegram_user_id,
        )
        return {
            "ok": True,
            "id": rid,
            "fire_at_local": format_local(fire_at_local),
            "text": text,
            "recurrence": recurrence,
        }

    async def _insert_pg(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        text: str,
        fire_at: datetime,
        agent_key: str,
        tz_name: str,
        recurrence: str = "once",
    ) -> int:
        from sqlalchemy import insert

        from src.agents_tg.db.models import Reminder

        async with self._pg_engine.begin() as conn:
            result = await conn.execute(
                insert(Reminder)
                .values(
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    agent_key=agent_key,
                    text=text,
                    fire_at=fire_at,
                    timezone_name=tz_name,
                    recurrence=recurrence,
                    status="pending",
                )
                .returning(Reminder.id)
            )
            row = result.first()
            return int(row[0])

    async def list_pending(self, telegram_user_id: int) -> list[dict[str, Any]]:
        if self._pg_engine:
            return await self._list_pending_pg(telegram_user_id)
        return [
            {
                "id": r.id,
                "text": r.text,
                "fire_at": format_local(r.fire_at),
                "status": r.status,
            }
            for r in self._memory
            if r.telegram_user_id == telegram_user_id and r.status == "pending"
        ]

    async def _list_pending_pg(self, telegram_user_id: int) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from src.agents_tg.db.models import Reminder

        async with self._pg_engine.connect() as conn:
            rows = await conn.execute(
                select(Reminder).where(
                    Reminder.telegram_user_id == telegram_user_id,
                    Reminder.status == "pending",
                )
            )
            return [
                {
                    "id": r.id,
                    "text": r.text,
                    "fire_at": format_local(r.fire_at),
                    "status": r.status,
                }
                for r in rows.scalars().all()
            ]

    async def start(self) -> None:
        """Start background poller + APScheduler for cron parity."""
        if self._poll_task and not self._poll_task.done():
            return
        self._poll_task = asyncio.create_task(self._poll_loop())
        await self._register_morning_digest()
        await self._start_apscheduler()
        logger.info("ReminderService started (poll + APScheduler + morning digest)")

    async def _start_apscheduler(self) -> None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            if self._scheduler is not None:
                return
            self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._fire_due,
                "interval",
                seconds=30,
                id="reminder_poll",
                replace_existing=True,
            )
            self._scheduler.start()
            logger.info("APScheduler started for reminder Task Brain")
        except ImportError:
            logger.debug("APScheduler not installed — using asyncio poll only")
        except Exception as exc:
            logger.warning("APScheduler start failed: %s", exc)

    async def stop(self) -> None:
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
            self._scheduler = None
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._fire_due()
            except Exception as exc:
                logger.exception("Reminder poll error: %s", exc)
            await asyncio.sleep(30)

    async def _fire_due(self) -> None:
        now = datetime.now(timezone.utc)
        if self._pg_engine:
            await self._fire_due_pg(now)
        else:
            for r in list(self._memory):
                if r.status == "pending" and r.fire_at <= now:
                    await self._deliver(
                        r.chat_id,
                        r.telegram_user_id,
                        r.text,
                        r.agent_key,
                        recurrence=r.recurrence,
                        reminder_id=r.id,
                    )
                    if r.recurrence == "daily":
                        r.fire_at = r.fire_at + timedelta(days=1)
                    else:
                        r.status = "sent"

    async def _fire_due_pg(self, now: datetime) -> None:
        from sqlalchemy import select, update

        from src.agents_tg.db.models import Reminder

        async with self._pg_engine.begin() as conn:
            rows = await conn.execute(
                select(Reminder).where(
                    Reminder.status == "pending",
                    Reminder.fire_at <= now,
                )
            )
            due = list(rows.scalars().all())
            for r in due:
                recurrence = getattr(r, "recurrence", "once") or "once"
                if recurrence == "daily":
                    from datetime import timedelta as _td

                    next_fire = r.fire_at + _td(days=1)
                    await conn.execute(
                        update(Reminder)
                        .where(Reminder.id == r.id)
                        .values(fire_at=next_fire, status="pending")
                    )
                else:
                    await conn.execute(
                        update(Reminder)
                        .where(Reminder.id == r.id)
                        .values(status="sent")
                    )
                await self._deliver(
                    r.chat_id,
                    r.telegram_user_id,
                    r.text,
                    r.agent_key,
                    recurrence=recurrence,
                    reminder_id=r.id,
                )

    async def _deliver(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        agent_key: str,
        *,
        recurrence: str = "once",
        reminder_id: int | None = None,
    ) -> None:
        is_digest = text.startswith(MORNING_DIGEST_MARKER)
        display = text[len(MORNING_DIGEST_MARKER) :] if is_digest else text

        if is_digest and self._digest_fn:
            try:
                await self._digest_fn(chat_id, user_id)
            except Exception as exc:
                logger.error("Digest delivery failed: %s", exc)
        elif self._cron_deliver_fn:
            try:
                await self._cron_deliver_fn(chat_id, user_id, display, agent_key)
            except Exception as exc:
                logger.error("Cron LLM delivery failed, static fallback: %s", exc)
                await self._deliver_static(chat_id, user_id, display, agent_key)
        else:
            await self._deliver_static(chat_id, user_id, display, agent_key)

        if is_digest:
            await self.schedule_morning_digest_if_missing(chat_id, user_id)

    async def _deliver_static(
        self,
        chat_id: int,
        user_id: int,
        display: str,
        agent_key: str,
    ) -> None:
        body = f"⏰ <b>Напоминание</b>\n{display}"
        if self._send_fn:
            try:
                await self._send_fn(chat_id, user_id, body, agent_key)
            except Exception as exc:
                logger.error("Reminder delivery failed: %s", exc)
        else:
            logger.warning("No send_fn for reminder to chat %s", chat_id)

    async def _register_morning_digest(self) -> None:
        """Reload pending digest reminders from PG on startup (no-op for memory)."""
        logger.debug("Morning digest cron uses poll + reschedule after fire")

    async def has_pending_digest(self, telegram_user_id: int) -> bool:
        pending = await self.list_pending(telegram_user_id)
        return any(
            (p.get("text") or "").startswith(MORNING_DIGEST_MARKER) for p in pending
        )

    async def schedule_morning_digest_if_missing(
        self, chat_id: int, user_id: int
    ) -> None:
        """Register recurring 09:00 MSK digest for a user."""
        if await self.has_pending_digest(user_id):
            return
        from src.agents_tg.utils.timezone_utils import now_local

        local = now_local()
        target = local.replace(hour=9, minute=0, second=0, microsecond=0)
        if local >= target:
            from datetime import timedelta

            target = target + timedelta(days=1)
        await self.schedule(
            telegram_user_id=user_id,
            chat_id=chat_id,
            text=MORNING_DIGEST_TEXT,
            fire_at_local=target,
            agent_key="personal_assistant",
            is_digest=True,
        )


reminder_service = ReminderService()
