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

        self.dp.message.middleware(RateLimitMiddleware(limit=3, window=60))

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

            is_group = message.chat.type in ["group", "supergroup"]
            is_mention = self._is_mentioned(message)

            # In groups, only respond to mentions
            if is_group and not is_mention:
                return

            coordinator = get_coordinator()
            user_text = self._extract_user_text(message)
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

            await state.set_state(AgentStates.processing)
            thinking_msg = await message.answer("🤖 Думаю...")

            try:
                response = await self._process_request(
                    message=message,
                    user_text=user_text,
                    is_group=is_group,
                    coordinator=coordinator,
                )

                if response:
                    if is_group:
                        await thinking_msg.delete()
                        sent = await message.reply(response)
                        coordinator.add_message(
                            message.chat.id,
                            GroupMessage(
                                message_id=sent.message_id,
                                from_agent=self.agent_key,
                                text=response,
                                timestamp=datetime.now(timezone.utc),
                                mentions=self._extract_mentions(response),
                            ),
                        )
                    else:
                        await thinking_msg.edit_text(response)
                else:
                    await thinking_msg.edit_text(
                        "😕 Не смог обработать запрос. Попробуйте переформулировать."
                    )

            except Exception as e:
                logger.error(
                    "Error processing message in %s: %s",
                    self.agent_key,
                    e,
                    exc_info=True,
                )
                await thinking_msg.edit_text(
                    "😕 Произошла ошибка. Попробуйте позже."
                )

            finally:
                await state.set_state(AgentStates.idle)

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

    async def _process_request(
        self,
        message: Message,
        user_text: str,
        is_group: bool,
        coordinator,
    ) -> Optional[str]:
        """Process the request using agent's specific logic."""
        group_context = ""
        if is_group:
            group_context = coordinator.get_recent_context(message.chat.id, 8)
            if group_context:
                user_text = (
                    f"Контекст группового чата:\n{group_context}\n\n"
                    f"Запрос пользователя: {user_text}"
                )

        if self.agent_key == "orchestrator":
            from src.agents_tg.agents.orchestrator import orchestrator

            return await orchestrator.process(
                user_text,
                user_id=str(message.from_user.id),
            )
        elif self.agent_key == "personal_assistant":
            from src.agents_tg.agents.personal_assistant import personal_assistant

            return await personal_assistant.process(
                user_text, user_id=str(message.from_user.id)
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
                    user_id=str(message.from_user.id),
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
