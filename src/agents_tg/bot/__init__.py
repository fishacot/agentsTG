"""Telegram bot handlers (legacy single-bot module).

Note: This module is kept for reference but not used in multi-bot architecture.
The multi-bot system is in src.agents_tg.bots package.
"""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


class BotStates(StatesGroup):
    """FSM states for the bot."""

    idle = State()
    waiting_for_input = State()


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    await state.set_state(BotStates.idle)
    await message.answer(
        "👋 Привет! Я AI Assistant с несколькими агентами.\n\n"
        "Доступные агенты:\n"
        "🧭 Оркестратор — распределение задач и контроль контекста\n"
        "📅 Личный помощник (Эльза) — задачи, заметки Obsidian, напоминания\n"
        "🔎 Ресерчер — поиск репозиториев/референсов/советов (интернет)\n"
        "🛡️ Security & AI — безопасность, архитектура, код-ревью\n"
        "💼 Бизнес — стратегия, планы, приоритизация\n"
        "📈 Маркетинг — позиционирование, контент, рост\n\n"
        "Просто напиши цель или задачу — я построю план "
        "и подключу нужных специалистов."
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 Список команд:\n\n"
        "/start — Начать работу\n"
        "/help — Показать эту справку\n"
        "/menu — Показать меню\n"
        "/team — Командный режим (Оркестратор + все агенты)\n"
        "/pa — Личный помощник\n"
        "/coder — Агент‑кодер/архитектор\n"
        "/research — Ресерчер\n"
        "/biz — Бизнес и проекты\n"
        "/mkt — Маркетинг и рост\n"
        "/sec — Безопасность и ИИ\n\n"
        "Просто опиши свою задачу, и я помогу!"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """Handle /menu command."""
    await message.answer(
        "📋 Выбери агента:",
        reply_markup={
            "inline_keyboard": [
                [
                    {
                        "text": "🧭 Оркестратор",
                        "callback_data": "agent_team",
                    },
                    {
                        "text": "📅 Помощник",
                        "callback_data": "agent_pa",
                    },
                ],
                [
                    {
                        "text": "💻 Coder",
                        "callback_data": "agent_coder",
                    },
                    {
                        "text": "🔎 Research",
                        "callback_data": "agent_research",
                    },
                ],
                [
                    {
                        "text": "💼 Business",
                        "callback_data": "agent_biz",
                    },
                    {
                        "text": "📈 Marketing",
                        "callback_data": "agent_mkt",
                    },
                ],
                [
                    {
                        "text": "🛡️ Security & AI",
                        "callback_data": "agent_sec",
                    },
                ],
            ]
        },
    )


@router.callback_query(lambda c: c.data.startswith("agent_"))
async def process_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle inline keyboard button presses."""
    agent_type = callback.data

    await callback.answer()

    if agent_type == "agent_team":
        await state.set_state(BotStates.waiting_for_input)
        await callback.message.answer(
            "🧭 Командный режим включен.\n\n"
            "Опиши цель или задачу — Оркестратор построит план и "
            "подключит нужных агентов шаг за шагом."
        )
    elif agent_type == "agent_pa":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "📅 Эльза (Ассистент) на связи.\n\n"
            "Задачи, заметки Obsidian и напоминания. "
            "Чем могу помочь?"
        )
    elif agent_type == "agent_coder":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "💻 Руслан (Coder) на связи.\n\n"
            "Я анализирую код, архитектуру и помогаю с разработкой. "
            "Опиши задачу или пришли код для ревью."
        )
    elif agent_type == "agent_research":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "🔎 Ульяна (Research) на связи.\n\n"
            "Я ищу репозитории, best practices, конкурентов и технические решения. "
            "Что нужно найти?"
        )
    elif agent_type == "agent_biz":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "💼 Ваня (Business) на связи.\n\n"
            "Я помогаю со стратегией, MVP-планами и приоритизацией. "
            "Опиши бизнес-задачу."
        )
    elif agent_type == "agent_mkt":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "📈 Тася (Marketing) на связи.\n\n"
            "Я помогаю с позиционированием, контентом и каналами роста. "
            "Что продвигаем?"
        )
    elif agent_type == "agent_sec":
        await state.set_state(BotStates.idle)
        await callback.message.answer(
            "🛡️ Артём (Security) на связи.\n\n"
            "Я анализирую безопасность кода и архитектуры. "
            "Пришли код для аудита или опиши систему."
        )
    else:
        await callback.message.answer("😕 Неизвестный агент. Попробуйте /menu")


@router.message(Command("team"))
async def cmd_team(message: Message, state: FSMContext) -> None:
    """Handle /team command - trigger orchestrator in team mode."""
    await state.set_state(BotStates.waiting_for_input)
    await message.answer(
        "🧭 Командный режим включен.\n\n"
        "Опиши цель или задачу — Оркестратор построит план и "
        "подключит нужных агентов шаг за шагом."
    )


@router.message(Command("pa"))
async def cmd_pa(message: Message, state: FSMContext) -> None:
    """Direct conversation with Personal Assistant."""
    from src.agents_tg.agents.personal_assistant import personal_assistant

    await state.set_state(BotStates.idle)
    response = await personal_assistant.process(
        message.text or "", user_id=str(message.from_user.id)
    )
    await message.answer(response)


@router.message(Command("coder"))
async def cmd_coder(message: Message, state: FSMContext) -> None:
    """Direct conversation with Coder agent."""
    from src.agents_tg.agents.specialists import coder

    await state.set_state(BotStates.idle)
    response = await coder.process(
        message.text or "", user_id=str(message.from_user.id)
    )
    await message.answer(response)


@router.message(Command("research"))
async def cmd_research(message: Message, state: FSMContext) -> None:
    """Direct conversation with Research agent."""
    from src.agents_tg.agents.specialists import research_analyst

    await state.set_state(BotStates.idle)
    response = await research_analyst.process(
        message.text or "",
        user_id=str(message.from_user.id),
    )
    await message.answer(response)


@router.message(Command("biz"))
async def cmd_biz(message: Message, state: FSMContext) -> None:
    """Direct conversation with Business & PM agent."""
    from src.agents_tg.agents.specialists import business_manager

    await state.set_state(BotStates.idle)
    response = await business_manager.process(
        message.text or "",
        user_id=str(message.from_user.id),
    )
    await message.answer(response)


@router.message(Command("mkt"))
async def cmd_mkt(message: Message, state: FSMContext) -> None:
    """Direct conversation with Marketing agent."""
    from src.agents_tg.agents.specialists import marketing

    await state.set_state(BotStates.idle)
    response = await marketing.process(
        message.text or "",
        user_id=str(message.from_user.id),
    )
    await message.answer(response)


@router.message(Command("sec"))
async def cmd_sec(message: Message, state: FSMContext) -> None:
    """Direct conversation with Security & AI agent."""
    from src.agents_tg.agents.specialists import security_ai

    await state.set_state(BotStates.idle)
    response = await security_ai.process(
        message.text or "",
        user_id=str(message.from_user.id),
    )
    await message.answer(response)


@router.message()
async def handle_message(message: Message, state: FSMContext) -> None:
    """Handle all other messages - pass to Orchestrator Agent."""
    user_text = message.text

    thinking_msg = await message.answer("🤖 Думаю...")

    from src.agents_tg.agents.orchestrator import orchestrator

    try:
        response = await orchestrator.process(
            user_text, user_id=str(message.from_user.id)
        )
        await thinking_msg.edit_text(response)
    except Exception as e:
        logger.error("Error processing message: %s", e)
        await thinking_msg.edit_text(
            "😕 Извини, произошла ошибка. Попробуй ещё раз."
        )
