"""Agent environment awareness — what the agent can 'see' in Telegram."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_identity import AGENT_IDENTITIES, get_agent_identity
from src.agents_tg.services.memory_service import memory_service

if TYPE_CHECKING:
    from aiogram.types import Message

    from src.agents_tg.bots.group_coordinator import GroupCoordinator


@dataclass
class AgentEnvironment:
    """Structured view of the agent's Telegram surroundings."""

    chat_type: str
    chat_id: int
    user_id: str
    user_username: str | None
    agent_key: str
    is_group: bool
    group_recent: str = ""
    dm_recent: str = ""
    tool_names: list[str] = field(default_factory=list)
    memory_facts_count: int = 0
    notes_channel_configured: bool = False
    vault_path: str = "vault"
    bootstrap_block: str = ""
    task_id: str | None = None
    session_id: str | None = None

    def to_prompt_block(self) -> str:
        identity = get_agent_identity(self.agent_key)
        human_name = identity.get("human_name") or self.agent_key
        colleagues = []
        for key, info in AGENT_IDENTITIES.items():
            if key != self.agent_key:
                uname = info.get("username", key)
                hname = info.get("human_name", key)
                colleagues.append(f"@{uname} ({hname})")

        mode = "групповой чат" if self.is_group else "личные сообщения (ЛС)"
        channel = (
            "настроен (можно post_to_notes_channel)"
            if self.notes_channel_configured
            else "не настроен"
        )
        tools = ", ".join(self.tool_names) if self.tool_names else "только диалог"

        lines = [
            "\n\n## СРЕДА (где ты сейчас)",
            f"- Ты: {human_name} (@{identity.get('username', self.agent_key)})",
            f"- Режим: {mode} (chat_type={self.chat_type})",
            f"- chat_id: {self.chat_id}",
            f"- user_id: {self.user_id}"
            + (f", @{self.user_username}" if self.user_username else ""),
            f"- Коллеги в команде: {', '.join(colleagues)}",
            f"- Канал заметок: {channel}",
            f"- Vault Obsidian: {self.vault_path}",
            f"- Фактов в памяти о пользователе: {self.memory_facts_count}",
            f"- Доступные инструменты: {tools}",
        ]
        if self.is_group and self.group_recent:
            lines.append(f"- Недавно в группе:\n{self.group_recent}")
        if not self.is_group and self.dm_recent:
            lines.append(f"- Недавний диалог в ЛС:\n{self.dm_recent}")
        lines.append(
            "- Действуй в рамках своей роли и этого чата. "
            "В группе отвечай сжато; в ЛС — развёрнуто."
        )
        base = "\n".join(lines)
        if self.bootstrap_block:
            return base + self.bootstrap_block
        return base


async def build_environment(
    *,
    message: Message,
    agent_key: str,
    coordinator: GroupCoordinator | None,
    tool_names: list[str] | None = None,
    dm_recent: str = "",
    group_context_lines: int = 18,
    user_message: str = "",
    task_id: str | None = None,
) -> AgentEnvironment:
    """Build environment context from a Telegram message."""
    from src.agents_tg.services.bootstrap_context import build_bootstrap_blocks
    from src.agents_tg.services.prompt_builder import detect_prompt_tier

    settings = get_settings()
    is_group = message.chat.type in ("group", "supergroup")
    user = message.from_user
    user_id = str(user.id) if user else "default"
    username = user.username if user else None
    tg_uid = int(user_id) if user_id.isdigit() else 0

    group_recent = ""
    if is_group and coordinator:
        group_recent = coordinator.get_recent_context(
            message.chat.id,
            n_messages=group_context_lines,
        )

    facts_raw = await memory_service.get_all(user_id)
    facts_count = len(facts_raw)
    fact_texts = [(item.get("text") or item.get("memory") or "") for item in facts_raw]
    fact_texts = [f for f in fact_texts if f]

    tier = detect_prompt_tier(user_message or dm_recent)
    include_web = agent_key in (
        "research",
        "coder",
        "security_ai",
        "business_manager",
        "marketing",
        "general",
    )
    if include_web:
        tier = detect_prompt_tier(user_message, include_web_tools=True)

    bootstrap = await build_bootstrap_blocks(
        telegram_user_id=tg_uid,
        agent_key=agent_key,
        tier=tier,
        identity_facts=fact_texts[:6],
        all_facts=fact_texts,
    )
    bootstrap_block = "".join(
        [
            bootstrap["time_block"],
            bootstrap["user_block"],
            bootstrap["focus_block"],
            bootstrap["memory_curated_block"],
            bootstrap["tools_block"],
        ]
    )

    return AgentEnvironment(
        chat_type=str(message.chat.type),
        chat_id=message.chat.id,
        user_id=user_id,
        user_username=username,
        agent_key=agent_key,
        is_group=is_group,
        group_recent=group_recent,
        dm_recent=dm_recent,
        tool_names=list(tool_names or []),
        memory_facts_count=facts_count,
        notes_channel_configured=bool(settings.NOTES_CHANNEL_ID),
        vault_path=settings.OBSIDIAN_VAULT_PATH,
        bootstrap_block=bootstrap_block,
        task_id=task_id,
    )


async def build_environment_scheduled(
    *,
    telegram_user_id: int,
    chat_id: int,
    agent_key: str,
    user_message: str = "",
    dm_recent: str = "",
) -> AgentEnvironment:
    """Build environment for proactive runs without a real Telegram Message."""
    from src.agents_tg.services.bootstrap_context import build_bootstrap_blocks
    from src.agents_tg.services.prompt_builder import detect_prompt_tier

    settings = get_settings()
    user_id = str(telegram_user_id)
    facts_raw = await memory_service.get_all(user_id)
    facts_count = len(facts_raw)
    fact_texts = [(item.get("text") or item.get("memory") or "") for item in facts_raw]
    fact_texts = [f for f in fact_texts if f]

    tier = detect_prompt_tier(user_message or dm_recent)
    bootstrap = await build_bootstrap_blocks(
        telegram_user_id=telegram_user_id,
        agent_key=agent_key,
        tier=tier,
        identity_facts=fact_texts[:6],
        all_facts=fact_texts,
    )
    bootstrap_block = "".join(
        [
            bootstrap["time_block"],
            bootstrap["user_block"],
            bootstrap["focus_block"],
            bootstrap["memory_curated_block"],
            bootstrap["tools_block"],
        ]
    )

    return AgentEnvironment(
        chat_type="private",
        chat_id=chat_id,
        user_id=user_id,
        user_username=None,
        agent_key=agent_key,
        is_group=False,
        group_recent="",
        dm_recent=dm_recent,
        tool_names=[],
        memory_facts_count=facts_count,
        notes_channel_configured=bool(settings.NOTES_CHANNEL_ID),
        vault_path=settings.OBSIDIAN_VAULT_PATH,
        bootstrap_block=bootstrap_block,
    )
