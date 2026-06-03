"""Slash-command handlers for individual agent bots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

if TYPE_CHECKING:
    from src.agents_tg.bots.agent_bot import AgentBot


def register_commands(router: Router, bot: AgentBot) -> None:
    """Register /start, /help, and utility commands on the agent router."""

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        from src.agents_tg.bots.agent_bot import AgentStates

        await state.set_state(AgentStates.idle)
        intro = bot.identity.get("intro_dm", f"👋 Привет! Я {bot.agent_key}")
        await message.answer(intro)
        if bot.agent_key == "personal_assistant" and message.from_user:
            from src.agents_tg.services.reminder_service import reminder_service

            await reminder_service.schedule_morning_digest_if_missing(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
            )

    @router.message(Command("help"))
    async def cmd_help(message: Message, state: FSMContext):
        colleagues = bot.get_colleagues_info()
        display_name = bot.identity.get("name", bot.agent_key)
        help_text = (
            f"📖 Я {display_name}.\n\n"
            f"Мои коллеги:\n{colleagues}\n\n"
            f"В группе упомяните меня @{bot.username} "
            f"или обращайтесь в личные сообщения."
        )
        await message.answer(help_text)

    @router.message(Command("colleagues"))
    async def cmd_colleagues(message: Message, state: FSMContext):
        await message.answer(bot.get_colleagues_full_info())

    @router.message(Command("about_me"))
    async def cmd_about_me(message: Message, state: FSMContext):
        about = bot.identity.get("about", f"Я {bot.agent_key}")
        await message.answer(about)

    @router.message(Command("journal"))
    async def cmd_journal(message: Message, state: FSMContext):
        if not message.from_user:
            return
        from src.agents_tg.services.workspace_memory import _workspace_root

        path = _workspace_root(message.from_user.id) / "JOURNAL.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")[-3500:]
            await message.answer(
                f"📓 <b>Журнал</b>\n<pre>{text[:3000]}</pre>", parse_mode="HTML"
            )
        else:
            await message.answer("Журнал пока пуст.")

    @router.message(Command("task"))
    async def cmd_task(message: Message, state: FSMContext):
        if not message.from_user:
            return
        from src.agents_tg.services.user_tasks_service import user_tasks_service

        tasks = await user_tasks_service.list_tasks(
            telegram_user_id=message.from_user.id
        )
        pending = [
            t for t in (tasks.get("tasks") or []) if t.get("status") == "pending"
        ]
        if not pending:
            await message.answer("Нет активных задач.")
            return
        lines = "\n".join(f"• {t.get('title', '?')}" for t in pending[:15])
        await message.answer(f"📋 <b>Задачи</b>\n{lines}", parse_mode="HTML")

    @router.message(Command("status"))
    async def cmd_status(message: Message, state: FSMContext):
        from src.agents_tg.services.health_server import _pg_status

        pg = await _pg_status()
        db = "✅ PG" if pg.get("connected") else "⚠️ без PG"
        await message.answer(f"🤖 {bot.agent_key}\n{db}")
