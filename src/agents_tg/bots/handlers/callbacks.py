"""Inline callback handlers for agent bots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.fsm.context import FSMContext

if TYPE_CHECKING:
    from src.agents_tg.bots.agent_bot import AgentBot


def register_callbacks(router: Router, bot: AgentBot) -> None:
    """Register confirmation and other callback queries."""

    @router.callback_query()
    async def on_callback(callback, state: FSMContext):
        data = callback.data or ""

        if data.startswith("plan_cancel:"):
            task_id = data.split(":", 1)[1]
            from src.agents_tg.services.plan_cancel import request_cancel

            request_cancel(task_id)
            await callback.message.edit_text("⏹ Задача отменена.")
            await callback.answer()
            return

        if not data.startswith("confirm:"):
            return

        parts = data.split(":")
        if len(parts) < 3:
            return

        token, decision = parts[1], parts[2]
        from src.agents_tg.services.confirmation_service import confirmation_service

        entry = confirmation_service.consume(token)
        if not entry:
            await callback.answer("Подтверждение устарело.", show_alert=True)
            return

        await confirmation_service.persist_consume(token)
        if decision == "yes":
            from src.agents_tg.services.confirmation_replay import (
                format_replay_message,
                replay_confirmed_action,
            )

            result = await replay_confirmed_action(entry)
            text = format_replay_message(result)
            await callback.message.edit_text(text)
        else:
            await callback.message.edit_text(f"❌ Отменено: {entry.action}")
        await callback.answer()
