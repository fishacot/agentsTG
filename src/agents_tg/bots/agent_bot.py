"""Individual agent bot implementation."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import ErrorEvent, Message

from src.agents_tg.bot.middlewares import RateLimitMiddleware
from src.agents_tg.bots.telegram_connection import TELEGRAM_CONNECT_SEMAPHORE
from src.agents_tg.services.agent_identity import get_agent_identity

logger = logging.getLogger(__name__)


class AgentStates(StatesGroup):
    """FSM states for agent bot."""

    idle = State()
    processing = State()


class AgentBot:
    """Individual Telegram bot for a specific agent.

    Each agent (Personal Assistant, Coder, Research, etc.) has its own
    Telegram bot with unique token and personality.
    """

    def __init__(
        self,
        agent_key: str,
        bot_token: str,
        username: str,  # @username for mentions
    ):
        self.agent_key = agent_key
        self.username = username.lower().replace("@", "")
        self.identity = get_agent_identity(agent_key)
        self._polling = False

        # Plain text — avoids HTML parse errors in intro messages
        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(),
        )
        self.dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT)
        self.router = Router()

        self._register_handlers()
        self._register_error_handler()
        self.dp.include_router(self.router)

        self.dp.message.middleware(RateLimitMiddleware(limit=5, window=60))

        logger.info("AgentBot initialized: %s (@%s)", agent_key, self.username)

    def _register_error_handler(self) -> None:
        """Log handler errors without stopping polling."""

        @self.dp.error()
        async def on_error(event: ErrorEvent):
            logger.error(
                "Telegram handler error in %s: %s",
                self.agent_key,
                event.exception,
                exc_info=event.exception,
            )
            return True

    def _register_handlers(self):
        """Register message handlers for this agent."""

        @self.router.message(CommandStart())
        async def cmd_start(message: Message, state: FSMContext):
            """Handle /start in private chat."""
            await state.set_state(AgentStates.idle)
            intro = self.identity.get("intro_dm", f"👋 Привет! Я {self.agent_key}")
            await message.answer(intro)
            if self.agent_key == "personal_assistant" and message.from_user:
                from src.agents_tg.services.reminder_service import reminder_service

                await reminder_service.schedule_morning_digest_if_missing(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                )

        @self.router.message(Command("help"))
        async def cmd_help(message: Message, state: FSMContext):
            """Handle /help command."""
            colleagues = self._get_colleagues_info()
            display_name = self.identity.get("name", self.agent_key)
            help_text = (
                f"📖 Я {display_name}.\n\n"
                f"Мои коллеги:\n{colleagues}\n\n"
                f"В группе упомяните меня @{self.username} "
                f"или обращайтесь в личные сообщения."
            )
            await message.answer(help_text)

        @self.router.message(Command("colleagues"))
        async def cmd_colleagues(message: Message, state: FSMContext):
            """Show information about colleague agents."""
            colleagues = self._get_colleagues_full_info()
            await message.answer(colleagues)

        @self.router.message(Command("about_me"))
        async def cmd_about_me(message: Message, state: FSMContext):
            """Show this agent's identity and capabilities."""
            about = self.identity.get("about", f"Я {self.agent_key}")
            await message.answer(about)

        @self.router.message()
        async def handle_message(message: Message, state: FSMContext):
            """Handle direct messages and group mentions."""
            from src.agents_tg.bots.group_coordinator import (
                GroupMessage,
                get_coordinator,
            )
            from src.agents_tg.config.settings import get_settings
            from src.agents_tg.services.message_pipeline import message_pipeline

            is_group = message.chat.type in ["group", "supergroup"]
            is_mention = self._is_mentioned(message)

            if is_group and not is_mention:
                return

            if await message_pipeline.is_duplicate(
                self.agent_key, message.chat.id, message.message_id
            ):
                return

            settings = get_settings()
            message_pipeline.debounce_sec = settings.MESSAGE_DEBOUNCE_MS / 1000.0

            async def _run_handler(msg: Message, *, combined_text: str | None = None):
                await self._handle_inbound(msg, state, combined_text=combined_text)

            if settings.MESSAGE_DEBOUNCE_MS > 0 and not is_group:
                await message_pipeline.enqueue_debounced(
                    agent_key=self.agent_key,
                    message=message,
                    handler=_run_handler,
                )
            elif message_pipeline.is_busy(self.agent_key, message.chat.id):
                message_pipeline.queue_followup(
                    agent_key=self.agent_key,
                    message=message,
                    handler=_run_handler,
                )
            else:
                await _run_handler(message)

    async def _handle_inbound(
        self,
        message: Message,
        state: FSMContext,
        *,
        combined_text: str | None = None,
    ) -> None:
        from src.agents_tg.bots.group_coordinator import GroupMessage, get_coordinator
        from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
        from src.agents_tg.services.agent_runtime import agent_runtime
        from src.agents_tg.services.background_runs import background_runs
        from src.agents_tg.services.message_pipeline import message_pipeline
        from src.agents_tg.services.orchestrator_delegate import maybe_delegate_async
        from src.agents_tg.utils.structured_log import log_event
        from src.agents_tg.utils.telegram_format import send_agent_response

        is_group = message.chat.type in ["group", "supergroup"]
        coordinator = get_coordinator()
        user_text = combined_text or self._extract_user_text(message)
        sender = "user" if message.from_user else "unknown"

        if is_group:
            coordinator.add_message(
                message.chat.id,
                GroupMessage(
                    message_id=message.message_id,
                    from_agent=sender,
                    text=user_text,
                    timestamp=datetime.now(timezone.utc),
                    mentions=self._extract_mentions(message.text or ""),
                ),
            )

        async with message_pipeline.run_lock(self.agent_key, message.chat.id):
            await state.set_state(AgentStates.processing)
            thinking_msg = await message.answer("🤖 Думаю...")
            log_event(
                "inbound_start",
                agent=self.agent_key,
                chat_id=message.chat.id,
                user_id=message.from_user.id if message.from_user else None,
                group=is_group,
            )

            try:
                # Background research for Ульяна on explicit search
                if self.agent_key == "research" and self._is_research_intent(user_text):
                    ack = await background_runs.run_research_background(
                        message=message,
                        user_text=user_text,
                        process_fn=self._process_request,
                        deliver_fn=self._deliver_extra_message,
                    )
                    profile = get_delivery_profile(self.agent_key)
                    await send_agent_response(
                        message,
                        ack,
                        reply_in_group=is_group,
                        thinking_message=thinking_msg,
                        chunk_limit=profile.text_chunk_limit,
                    )
                    return

                run_result = await agent_runtime.run_inbound(
                    agent_key=self.agent_key,
                    process_fn=self._process_request,
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

                profile = get_delivery_profile(self.agent_key)
                primary = run_result.primary or ""

                if is_group and primary:
                    if coordinator.should_skip_echo(
                        message.chat.id, self.agent_key, primary
                    ):
                        log_event(
                            "anti_echo_skip",
                            agent=self.agent_key,
                            chat_id=message.chat.id,
                        )
                        await thinking_msg.delete()
                        return

                if (
                    self.agent_key == "orchestrator"
                    and is_group
                    and primary
                ):
                    plan = coordinator.get_plan(message.chat.id)
                    primary = await maybe_delegate_async(
                        plan=plan,
                        primary_reply=primary,
                        message=message,
                        user_text=user_text,
                        process_fn=self._process_request,
                        deliver_fn=self._deliver_extra_message,
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

                if is_group and sent and primary:
                    coordinator.add_message(
                        message.chat.id,
                        GroupMessage(
                            message_id=sent.message_id,
                            from_agent=self.agent_key,
                            text=primary,
                            timestamp=datetime.now(timezone.utc),
                            mentions=self._extract_mentions(primary),
                        ),
                    )

                log_event(
                    "inbound_done",
                    agent=self.agent_key,
                    chat_id=message.chat.id,
                    parts=1 + len(run_result.extras),
                )

                await self._auto_log_project_activity(message, primary)

            except Exception as e:
                from src.agents_tg.services.llm_client import QwenAPIError, RateLimitError

                logger.error(
                    "Error processing message in %s: %s",
                    self.agent_key,
                    e,
                    exc_info=True,
                )
                if isinstance(e, (RateLimitError, QwenAPIError)) and (
                    getattr(e, "status", 0) == 429 or getattr(e, "retryable", False)
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
                await message_pipeline.drain_followups(
                    self.agent_key, message.chat.id
                )

    @staticmethod
    def _is_research_intent(text: str) -> bool:
        low = text.lower()
        markers = (
            "найди",
            "поиск",
            "новост",
            "актуальн",
            "сравни",
            "research",
            "search",
        )
        return any(m in low for m in markers)

    async def _deliver_extra_message(self, message: Message, text: str) -> None:
        from src.agents_tg.services.agent_delivery_profile import get_delivery_profile
        from src.agents_tg.utils.telegram_format import send_agent_response

        profile = get_delivery_profile(self.agent_key)
        await send_agent_response(
            message,
            text,
            reply_in_group=False,
            thinking_message=None,
            chunk_limit=profile.text_chunk_limit,
        )

    def _is_mentioned(self, message: Message) -> bool:
        """Check if this bot is mentioned in the message."""
        if not message.text:
            return False

        text_lower = message.text.lower()
        if f"@{self.username}" in text_lower:
            return True

        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mention = message.text[
                        entity.offset : entity.offset + entity.length
                    ].lower()
                    if mention == f"@{self.username}":
                        return True

        return False

    def _extract_user_text(self, message: Message) -> str:
        """Remove bot mention from message text."""
        text = (message.text or "").strip()
        if not text:
            return ""

        pattern = re.compile(rf"@?{re.escape(self.username)}\b", re.IGNORECASE)
        cleaned = pattern.sub("", text).strip()
        return cleaned or text

    @staticmethod
    def _extract_mentions(text: str) -> list[str]:
        """Extract @username mentions from text."""
        return re.findall(r"@([A-Za-z0-9_]+)", text)

    def _get_colleagues_info(self) -> str:
        """Get short info about colleague agents."""
        from src.agents_tg.services.agent_identity import AGENT_IDENTITIES

        colleagues = []
        for key, identity in AGENT_IDENTITIES.items():
            if key != self.agent_key:
                username = identity.get("username", key)
                short_desc = identity.get("short_desc", "Агент")
                colleagues.append(f"  • @{username} — {short_desc}")

        return "\n".join(colleagues) if colleagues else "  (нет коллег)"

    def _get_colleagues_full_info(self) -> str:
        """Get full info about colleague agents for collaboration."""
        from src.agents_tg.services.agent_identity import AGENT_IDENTITIES

        lines = ["👥 Мои коллеги-агенты:\n"]

        for key, identity in AGENT_IDENTITIES.items():
            if key != self.agent_key:
                username = identity.get("username", key)
                name = identity.get("name", key)
                desc = identity.get("description", "")
                role = identity.get("role", "")

                lines.append(f"\n🤖 @{username}")
                lines.append(f"   Имя: {name}")
                lines.append(f"   Роль: {role}")
                lines.append(f"   Описание: {desc}")
                lines.append(
                    f"   Когда привлекать: {identity.get('when_to_invoke', '')}"
                )

        lines.append(f"\n💡 В группе упоминайте @{self.username} для обращения ко мне")
        lines.append("💡 Используйте @username коллеги для привлечения их")

        return "\n".join(lines)

    def _tool_names_for_agent(self) -> list[str]:
        """Tool names exposed to environment context."""
        common = [
            "remember_about_user",
            "log_project_activity",
            "update_project_status",
        ]
        if self.agent_key == "personal_assistant":
            return [
                "create_obsidian_note",
                "post_to_notes_channel",
                "add_task",
                "list_tasks",
                "schedule_reminder",
                "send_telegram_message",
                "update_user_profile",
                "set_active_project",
                *common,
            ]
        if self.agent_key == "orchestrator":
            return [
                "delegation",
                "send_telegram_message",
                "update_user_profile",
                "set_active_project",
                *common,
            ]
        return ["deep_research", "send_telegram_message", *common]

    async def _auto_log_project_activity(
        self,
        message: Message,
        reply_text: str,
    ) -> None:
        """Cross-agent journal entry after a successful run."""
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
            agent_key=self.agent_key,
            summary=summary,
            kind=kind_map.get(self.agent_key, "note"),
            project_id=project["id"],
        )

    async def _process_request(
        self,
        message: Message,
        user_text: str,
        is_group: bool,
        coordinator,
    ) -> Optional[str]:
        """Process the request using agent's specific logic."""
        from src.agents_tg.services.chat_history import chat_history
        from src.agents_tg.services.environment_context import build_environment

        user_id = str(message.from_user.id) if message.from_user else "default"

        if is_group:
            group_context = coordinator.get_recent_context(message.chat.id, 18)
            if group_context:
                user_text = (
                    f"Контекст группового чата:\n{group_context}\n\n"
                    f"Запрос пользователя: {user_text}"
                )
            dm_recent = ""
        else:
            turns = await chat_history.get_recent(user_id, self.agent_key)
            dm_recent = chat_history.format_for_prompt(turns)

        environment = await build_environment(
            message=message,
            agent_key=self.agent_key,
            coordinator=coordinator if is_group else None,
            tool_names=self._tool_names_for_agent(),
            dm_recent=dm_recent,
            group_context_lines=18,
            user_message=user_text,
        )

        if self.agent_key == "orchestrator":
            from src.agents_tg.agents.orchestrator import orchestrator

            return await orchestrator.process(
                user_text,
                user_id=user_id,
                environment=environment,
            )
        elif self.agent_key == "personal_assistant":
            from src.agents_tg.agents.personal_assistant import personal_assistant

            return await personal_assistant.process(
                user_text,
                user_id=user_id,
                environment=environment,
            )
        else:
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

            agent = agent_map.get(self.agent_key)
            if agent:
                return await agent.process(
                    user_text,
                    user_id=user_id,
                    environment=environment,
                )

        return None

    async def start(self):
        """Start this bot's polling."""
        logger.info("Starting bot: %s (@%s)", self.agent_key, self.username)

        async with TELEGRAM_CONNECT_SEMAPHORE:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
            except TelegramNetworkError as exc:
                logger.warning(
                    "Webhook delete failed for %s: %s — continuing to polling",
                    self.agent_key,
                    exc,
                )

        self._polling = True
        try:
            await self.dp.start_polling(self.bot, handle_signals=False)
        finally:
            self._polling = False

    async def stop(self):
        """Stop this bot gracefully."""
        logger.info("Stopping bot: %s", self.agent_key)
        if self._polling:
            try:
                await self.dp.stop_polling()
            except RuntimeError:
                pass
        await self.bot.session.close()

    async def send_message_to_group(
        self, group_id: int, text: str, reply_to: Optional[int] = None
    ):
        """Send message to group chat (for inter-bot communication)."""
        try:
            await self.bot.send_message(
                chat_id=group_id,
                text=text,
                reply_to_message_id=reply_to,
            )
        except Exception as e:
            logger.error(f"Failed to send message to group from {self.agent_key}: {e}")
