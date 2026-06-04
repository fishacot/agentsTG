"""Inbound turn orchestration — gateway dispatch, agent run, Telegram delivery."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.agents_tg.bots.handlers.inbound import (
    extract_mentions,
    extract_user_text,
    is_research_intent,
)
from src.agents_tg.gateway.envelope import OpenClawEnvelope

if TYPE_CHECKING:
    from src.agents_tg.bots.agent_bot import AgentBot

logger = logging.getLogger(__name__)


class InboundTurnService:
    """Execute one inbound user turn: envelope → agent → delivery."""

    async def handle(
        self,
        bot: AgentBot,
        message: Message,
        state: FSMContext,
        *,
        combined_text: str | None = None,
    ) -> None:
        from src.agents_tg.bots.agent_bot import AgentStates
        from src.agents_tg.bots.group_coordinator import GroupMessage, get_coordinator
        from src.agents_tg.channels.telegram_adapter import from_update
        from src.agents_tg.gateway.router import gateway_router
        from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
        from src.agents_tg.services.agent_runtime import agent_runtime
        from src.agents_tg.services.background_runs import background_runs
        from src.agents_tg.services.message_pipeline import message_pipeline
        from src.agents_tg.services.orchestrator_delegate import maybe_delegate_async
        from src.agents_tg.utils.structured_log import log_event
        from src.agents_tg.utils.telegram_format import send_agent_response

        is_group = message.chat.type in ["group", "supergroup"]
        coordinator = get_coordinator()
        user_text = combined_text or extract_user_text(message, bot.username)
        sender = "user" if message.from_user else "unknown"

        if not is_group and message.from_user:
            from src.agents_tg.services.user_contact_service import user_contact_service

            await user_contact_service.record_inbound(
                telegram_user_id=message.from_user.id,
                chat_id=message.chat.id,
                agent_key=bot.agent_key,
            )

        if is_group:
            coordinator.add_message(
                message.chat.id,
                GroupMessage(
                    message_id=message.message_id,
                    from_agent=sender,
                    text=user_text,
                    timestamp=datetime.now(timezone.utc),
                    mentions=extract_mentions(message.text or ""),
                ),
            )

        envelope = from_update(message, bot.agent_key)
        if combined_text:
            envelope = envelope.model_copy(update={"text": combined_text})
        dispatch = await gateway_router.dispatch(envelope, trigger="inbound")
        if dispatch.duplicate:
            log_event(
                "inbound_duplicate_skip",
                agent=bot.agent_key,
                chat_id=message.chat.id,
                message_id=message.message_id,
            )
            return

        bound = dispatch.envelope or envelope
        job_failed = False

        async with message_pipeline.run_lock(bot.agent_key, message.chat.id):
            await gateway_router.start_job(dispatch.job_id)
            await state.set_state(AgentStates.processing)
            thinking_msg = await message.answer("🤖 Думаю...")
            log_event(
                "inbound_start",
                agent=bot.agent_key,
                chat_id=message.chat.id,
                user_id=message.from_user.id if message.from_user else None,
                group=is_group,
            )

            try:
                if bot.agent_key == "research" and is_research_intent(user_text):
                    ack = await background_runs.run_research_background(
                        message=message,
                        user_text=user_text,
                        process_fn=self._make_process_fn(bot, bound),
                        deliver_fn=lambda msg, text, **kw: self._deliver_extra_message(
                            bot, msg, text, **kw
                        ),
                    )
                    profile = get_delivery_profile(bot.agent_key)
                    await send_agent_response(
                        message,
                        ack,
                        reply_in_group=is_group,
                        thinking_message=thinking_msg,
                        chunk_limit=profile.text_chunk_limit,
                    )
                    return

                run_result = await agent_runtime.run_inbound(
                    agent_key=bot.agent_key,
                    process_fn=self._make_process_fn(bot, bound),
                    message=message,
                    user_text=user_text,
                    is_group=is_group,
                    coordinator=coordinator,
                )

                if run_result.silent:
                    await thinking_msg.delete()
                    return

                if not run_result.messages:
                    await thinking_msg.edit_text(
                        "😕 Не смог обработать запрос. Попробуйте переформулировать."
                    )
                    return

                profile = get_delivery_profile(bot.agent_key)
                primary = run_result.primary or ""

                if is_group and primary:
                    if coordinator.should_skip_echo(
                        message.chat.id, bot.agent_key, primary
                    ):
                        log_event(
                            "anti_echo_skip",
                            agent=bot.agent_key,
                            chat_id=message.chat.id,
                        )
                        await thinking_msg.delete()
                        return

                if bot.agent_key == "orchestrator" and primary:
                    plan = coordinator.get_plan(message.chat.id)
                    primary = await maybe_delegate_async(
                        plan=plan,
                        primary_reply=primary,
                        message=message,
                        user_text=user_text,
                        process_fn=self._make_process_fn(bot, bound),
                        deliver_fn=lambda msg, text, **kw: self._deliver_extra_message(
                            bot, msg, text, **kw
                        ),
                    )

                sent = await send_agent_response(
                    message,
                    primary,
                    reply_in_group=is_group,
                    thinking_message=thinking_msg,
                    chunk_limit=profile.text_chunk_limit,
                )

                for extra in run_result.extras:
                    await send_agent_response(
                        message,
                        extra,
                        reply_in_group=is_group,
                        thinking_message=None,
                        chunk_limit=profile.text_chunk_limit,
                    )

                for conf in run_result.confirmations:
                    await send_agent_response(
                        message,
                        conf.text,
                        reply_in_group=is_group,
                        thinking_message=None,
                        chunk_limit=profile.text_chunk_limit,
                        reply_markup=conf.reply_markup,
                        reply_to_message_id=message.message_id,
                    )

                if is_group and sent and primary:
                    coordinator.add_message(
                        message.chat.id,
                        GroupMessage(
                            message_id=sent.message_id,
                            from_agent=bot.agent_key,
                            text=primary,
                            timestamp=datetime.now(timezone.utc),
                            mentions=extract_mentions(primary),
                        ),
                    )

                log_event(
                    "inbound_done",
                    agent=bot.agent_key,
                    chat_id=message.chat.id,
                    parts=1 + len(run_result.extras),
                )

                if not is_group and message.from_user and (run_result.messages or sent):
                    from src.agents_tg.services.user_contact_service import (
                        user_contact_service,
                    )

                    await user_contact_service.record_outbound(
                        telegram_user_id=message.from_user.id,
                        agent_key=bot.agent_key,
                    )

                await self._auto_log_project_activity(bot, message, primary)

            except Exception as exc:
                job_failed = True
                from src.agents_tg.services.llm_client import (
                    QwenAPIError,
                    RateLimitError,
                )

                logger.error(
                    "Error processing message in %s: %s",
                    bot.agent_key,
                    exc,
                    exc_info=True,
                )
                if isinstance(exc, (RateLimitError, QwenAPIError)) and (
                    getattr(exc, "status", 0) == 429 or getattr(exc, "retryable", False)
                ):
                    await thinking_msg.edit_text(
                        "⏳ Сейчас перегрузка AI (лимит запросов). "
                        "Подождите 10–15 секунд и повторите."
                    )
                else:
                    await thinking_msg.edit_text(
                        "😕 Произошла ошибка. Попробуйте позже."
                    )

            finally:
                await state.set_state(AgentStates.idle)
                await message_pipeline.drain_followups(bot.agent_key, message.chat.id)
                if dispatch.job_id:
                    if job_failed:
                        await gateway_router.fail_job(dispatch.job_id)
                    else:
                        await gateway_router.complete_job(dispatch.job_id)

    def _make_process_fn(self, bot: AgentBot, envelope: OpenClawEnvelope):
        """Build process_fn that routes through gateway dispatch_agent."""

        async def process_fn(
            message: Message,
            user_text: str,
            is_group: bool,
            coordinator: Any,
        ) -> Optional[str]:
            from src.agents_tg.gateway.agent_dispatch import dispatch_agent

            return await dispatch_agent(
                envelope,
                message=message,
                user_text=user_text,
                coordinator=coordinator,
            )

        return process_fn

    async def _deliver_extra_message(
        self,
        bot: AgentBot,
        message: Message,
        text: str,
        *,
        reply_markup: dict | None = None,
        reply_to_message_id: int | None = None,
    ) -> None:
        from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
        from src.agents_tg.utils.telegram_format import send_agent_response

        profile = get_delivery_profile(bot.agent_key)
        await send_agent_response(
            message,
            text,
            reply_in_group=False,
            thinking_message=None,
            chunk_limit=profile.text_chunk_limit,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id or message.message_id,
        )

    async def _auto_log_project_activity(
        self,
        bot: AgentBot,
        message: Message,
        reply_text: str,
    ) -> None:
        if not message.from_user or not reply_text:
            return
        from src.agents_tg.services.shared_context import shared_context

        uid = message.from_user.id
        project = await shared_context.get_active_project(uid)
        if not project:
            return
        plain = re.sub(r"<[^>]+>", "", reply_text)
        summary = plain.strip()[:200]
        if len(summary) < 20:
            return
        kind_map = {
            "research": "research",
            "coder": "code",
            "business_manager": "plan",
            "marketing": "marketing",
            "security_ai": "security",
            "orchestrator": "delegation",
            "personal_assistant": "note",
        }
        await shared_context.log_activity(
            uid,
            agent_key=bot.agent_key,
            summary=summary,
            kind=kind_map.get(bot.agent_key, "note"),
            project_id=project["id"],
        )


inbound_turn_service = InboundTurnService()
