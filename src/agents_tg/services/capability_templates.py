"""Static HTML replies for common meta-questions (no LLM call)."""

from __future__ import annotations

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_identity import AGENT_IDENTITIES
from src.agents_tg.services.environment_context import AgentEnvironment


def build_elza_capabilities_html(environment: AgentEnvironment | None = None) -> str:
    """Manus-style capability overview for Эльза without LLM."""
    settings = get_settings()
    channel = (
        "настроен — могу публиковать заметки в Telegram-канал"
        if (environment and environment.notes_channel_configured)
        or settings.NOTES_CHANNEL_ID
        else "не настроен — только vault на сервере"
    )
    colleagues = []
    for key, info in AGENT_IDENTITIES.items():
        if key == "personal_assistant":
            continue
        uname = info.get("username", key)
        hname = info.get("human_name", key)
        short = info.get("short_desc", "")
        colleagues.append(f"• @{uname} — {hname}, {short}")

    team = "\n".join(colleagues)

    return (
        "<b>Я Эльза</b> — ваш личный ассистент. Помогаю навести порядок, "
        "не отвлекая от главного.\n\n"
        "<b>Чем могу помочь:</b>\n"
        "• <b>Заметки</b> — Obsidian vault на сервере\n"
        f"• <b>Канал заметок</b> — {channel}\n"
        "• <b>Задачи</b> — список дел и напоминания\n"
        "• <b>Память</b> — запоминаю факты о вас, если вы их сообщаете\n\n"
        "<b>Как просить:</b>\n"
        "«Запиши заметку …», «Добавь задачу …», «Покажи мои дела»\n\n"
        "<b>Коллеги</b> (если нужен код, поиск, бизнес):\n"
        f"{team}\n\n"
        "<i>Что сделаем первым?</i>"
    )


def build_elza_memory_faq_html() -> str:
    """Answer «можешь запоминать?» without LLM."""
    return (
        "<b>Да, могу запоминать.</b>\n\n"
        "Если вы расскажете о себе факт — я сохраню его и учту в следующих "
        "разговорах. Например: «Запомни, что я программист» или "
        "«Я живу в Москве».\n\n"
        "На вопрос «ты помнишь?» без нового факта — просто отвечаю, "
        "не создаю заметку.\n\n"
        "<i>Расскажите что-нибудь о себе — запомню.</i>"
    )


def build_egor_greeting_html() -> str:
    """Static greeting for Егор orchestrator (no LLM call)."""
    colleagues = []
    for key, info in AGENT_IDENTITIES.items():
        if key == "orchestrator":
            continue
        uname = info.get("username", key)
        hname = info.get("human_name", key)
        colleagues.append(f"• @{uname} — {hname}")
    team = "\n".join(colleagues)
    return (
        "Привет! Я <b>Егор</b>, координирую команду из шести специалистов.\n\n"
        "<b>Могу помочь с:</b> планом, кодом, исследованием, безопасностью, "
        "бизнесом и маркетингом.\n\n"
        f"<b>Команда:</b>\n{team}\n\n"
        "<i>Чем займёмся?</i>"
    )
