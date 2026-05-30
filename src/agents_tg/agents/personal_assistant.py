"""Personal Assistant Agent - manages Obsidian, Calendar, and Tasks."""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.agent_prompts import MANUS_PA_STYLE
from src.agents_tg.services.agent_runner import AgentTool, agent_runner, tool_result
from src.agents_tg.utils.git_sync import obsidian_sync

logger = logging.getLogger(__name__)
settings = get_settings()

_PLACEHOLDER_TITLES = frozenset(
    {"title", "[title]", "заметка", "note", "untitled", "без названия"}
)


class PersonalAssistant:
    """Agent for managing personal life (Obsidian, Tasks, Calendar)."""

    def __init__(self) -> None:
        self.obsidian_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "vault")
        if not os.path.exists(self.obsidian_vault_path):
            os.makedirs(self.obsidian_vault_path)

        self._soul_path = Path(__file__).parent / "souls" / "personal_assistant.md"
        self.tasks: List[Dict[str, Any]] = []

    def _load_soul(self) -> str:
        if self._soul_path.exists():
            return self._soul_path.read_text(encoding="utf-8")
        return ""

    def _valid_note_title(self, title: str) -> bool:
        cleaned = title.strip().lower()
        if not cleaned or cleaned.startswith("["):
            return False
        if cleaned in _PLACEHOLDER_TITLES:
            return False
        if re.fullmatch(r"[\W_]+", cleaned):
            return False
        return True

    async def create_obsidian_note(
        self, title: str, content: str, folder: str = "Inbox"
    ) -> dict[str, Any]:
        """Create a new note in Obsidian vault and sync."""
        if not self._valid_note_title(title):
            return {"ok": False, "error": "invalid_title", "title": title}

        obsidian_sync.pull()

        folder_path = os.path.join(self.obsidian_vault_path, folder)
        os.makedirs(folder_path, exist_ok=True)

        safe_title = title.strip()
        file_path = os.path.join(folder_path, f"{safe_title}.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                f"created: {datetime.now().isoformat()}\n"
                "tags: [ai-assistant]\n"
                "---\n\n"
            )
            f.write(content)

        sync_res = obsidian_sync.sync(f"Create note: {safe_title}")
        sync_error = sync_res if "Error" in sync_res else None

        return {
            "ok": True,
            "title": safe_title,
            "folder": folder,
            "path": file_path,
            "vault_root": self.obsidian_vault_path,
            "sync_error": sync_error,
        }

    async def add_task(self, title: str, due_date: Optional[str] = None) -> dict[str, Any]:
        """Add a task to ToDo list."""
        task = {
            "title": title,
            "due_date": due_date,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        self.tasks.append(task)
        return {
            "ok": True,
            "title": title,
            "due_date": due_date,
            "total_tasks": len(self.tasks),
        }

    async def list_tasks(self) -> dict[str, Any]:
        """List current tasks."""
        return {
            "ok": True,
            "tasks": [
                {
                    "title": t["title"],
                    "due_date": t["due_date"],
                    "status": t["status"],
                }
                for t in self.tasks
            ],
        }

    def _tools(self, chat_id: int = 0, telegram_user_id: int = 0) -> list[AgentTool]:
        pa = self
        cid = chat_id
        uid = telegram_user_id

        async def create_note(**kwargs: Any) -> str:
            title = str(kwargs.get("title", "")).strip()
            content = str(kwargs.get("content", "")).strip()
            folder = str(kwargs.get("folder", "Inbox")).strip() or "Inbox"
            if not pa._valid_note_title(title):
                return tool_result(
                    ok=False,
                    error="invalid_title",
                    hint="Пользователь не просил создать заметку или заголовок не задан.",
                )
            if not content:
                content = title
            data = await pa.create_obsidian_note(title, content, folder=folder)
            return tool_result(**data)

        async def add_task_handler(**kwargs: Any) -> str:
            title = str(kwargs.get("title", "")).strip()
            due_date = kwargs.get("due_date")
            if not title:
                return tool_result(ok=False, error="empty_title")
            data = await pa.add_task(
                title, due_date=str(due_date) if due_date else None
            )
            return tool_result(**data)

        async def list_tasks_handler(**kwargs: Any) -> str:
            data = await pa.list_tasks()
            return tool_result(**data)

        async def schedule_reminder_handler(**kwargs: Any) -> str:
            from src.agents_tg.services.reminder_parse import parse_reminder_when
            from src.agents_tg.services.reminder_service import reminder_service

            text = str(kwargs.get("text", "")).strip()
            when_raw = str(kwargs.get("when", "")).strip()
            if not text:
                return tool_result(ok=False, error="empty_text")
            fire_at = parse_reminder_when(when_raw)
            if fire_at is None:
                return tool_result(
                    ok=False,
                    error="invalid_when",
                    hint="Пример when: «через 5 минут», «в 11:00», «завтра 9:00»",
                )
            tg_uid = int(kwargs.get("telegram_user_id") or uid or 0)
            chat = int(kwargs.get("chat_id") or cid or 0)
            if not chat or not tg_uid:
                return tool_result(ok=False, error="missing_chat_context")
            data = await reminder_service.schedule(
                telegram_user_id=tg_uid,
                chat_id=chat,
                text=text,
                fire_at_local=fire_at,
            )
            return tool_result(**data)

        async def post_channel(**kwargs: Any) -> str:
            from src.agents_tg.services.telegram_notes import post_to_notes_channel

            title = str(kwargs.get("title", "")).strip()
            body = str(kwargs.get("body", "")).strip()
            if not pa._valid_note_title(title):
                return tool_result(ok=False, error="invalid_title")
            if not body:
                body = title
            data = await post_to_notes_channel(title, body)
            return tool_result(**data)

        tools = [
            AgentTool(
                name="create_obsidian_note",
                description=(
                    "Создать файл заметки в Obsidian vault. "
                    "Вызывай ТОЛЬКО если пользователь явно попросил записать, "
                    "сохранить или создать заметку. "
                    "НЕ вызывай на вопросы о возможностях, памяти, приветствия."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Заголовок заметки"},
                        "content": {
                            "type": "string",
                            "description": "Текст заметки",
                        },
                        "folder": {
                            "type": "string",
                            "description": "Папка в vault, по умолчанию Inbox",
                        },
                    },
                    "required": ["title", "content"],
                },
                handler=create_note,
            ),
            AgentTool(
                name="add_task",
                description=(
                    "Добавить задачу — только при явной просьбе пользователя."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Название задачи"},
                        "due_date": {
                            "type": "string",
                            "description": "Срок (необязательно)",
                        },
                    },
                    "required": ["title"],
                },
                handler=add_task_handler,
            ),
            AgentTool(
                name="list_tasks",
                description=(
                    "Показать список задач пользователя — ТОЛЬКО когда он явно просит "
                    "«покажи дела», «мои задачи», «список дел». "
                    "НЕ вызывай на новости, сводки, вопросы о себе или общий разговор."
                ),
                parameters={"type": "object", "properties": {}},
                handler=list_tasks_handler,
            ),
            AgentTool(
                name="schedule_reminder",
                description=(
                    "Запланировать напоминание в Telegram на указанное время (МСК). "
                    "ОБЯЗАТЕЛЬНО при «напомни», «пингни в …». Без этого инструмента "
                    "не обещай, что напомнишь."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Текст напоминания"},
                        "when": {
                            "type": "string",
                            "description": "Когда: «через 10 минут», «в 11:00», «завтра 9:00»",
                        },
                    },
                    "required": ["text", "when"],
                },
                handler=schedule_reminder_handler,
            ),
            AgentTool(
                name="post_to_notes_channel",
                description=(
                    "Опубликовать заметку в Telegram-канал пользователя. "
                    "Только при явной просьбе записать/сохранить и если канал настроен в среде."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Заголовок"},
                        "body": {"type": "string", "description": "Текст заметки"},
                    },
                    "required": ["title", "body"],
                },
                handler=post_channel,
            ),
        ]
        return tools

    async def process(
        self,
        message: str,
        user_id: str = "default",
        environment=None,
        environment_block: str = "",
    ) -> str:
        """Understand the user's goal; LLM formulates every user-visible reply."""
        from src.agents_tg.services.environment_context import AgentEnvironment

        from src.agents_tg.services.check_in_cooldown import check_in_cooldown
        from src.agents_tg.services.prompt_builder import PromptTier, detect_prompt_tier
        from src.agents_tg.services.shared_context import shared_context

        env = environment if isinstance(environment, AgentEnvironment) else None
        chat_id = env.chat_id if env else 0
        tg_uid = int(user_id) if user_id.isdigit() else 0

        hints = MANUS_PA_STYLE
        tier = detect_prompt_tier(message)
        if (
            tier == PromptTier.LIGHT
            and tg_uid
            and await shared_context.get_active_project(tg_uid)
            and await check_in_cooldown.should_offer_checkin(user_id)
        ):
            hints += (
                "\n\n## Check-in по проекту\n"
                "Если пользователь просто здоровается — один тёплый вопрос "
                "о прогрессе активного проекта (из блока ФОКУС). Не навязчиво.\n"
            )
            await check_in_cooldown.record_checkin(user_id)
        return await agent_runner.run(
            agent_key="personal_assistant",
            soul=self._load_soul(),
            user_message=message,
            user_id=user_id,
            tools=self._tools(chat_id=chat_id, telegram_user_id=tg_uid),
            output_hints=hints,
            environment=env,
            environment_block=environment_block,
            temperature=0.55,
            max_tokens=768,
        )


personal_assistant = PersonalAssistant()
