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
from src.agents_tg.services.capability_templates import build_elza_capabilities_html
from src.agents_tg.services.chat_history import chat_history
from src.agents_tg.services.prompt_builder import is_capabilities_question
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

    def _tools(self) -> list[AgentTool]:
        pa = self

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
                description="Показать задачи — когда пользователь просит список дел.",
                parameters={"type": "object", "properties": {}},
                handler=list_tasks_handler,
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

        env = environment if isinstance(environment, AgentEnvironment) else None

        if is_capabilities_question(message):
            reply = build_elza_capabilities_html(env)
            await chat_history.append(user_id, "personal_assistant", "user", message)
            await chat_history.append(user_id, "personal_assistant", "assistant", reply)
            return reply

        return await agent_runner.run(
            agent_key="personal_assistant",
            soul=self._load_soul(),
            user_message=message,
            user_id=user_id,
            tools=self._tools(),
            output_hints=MANUS_PA_STYLE,
            environment=env,
            environment_block=environment_block,
            temperature=0.55,
            max_tokens=1024,
        )


personal_assistant = PersonalAssistant()
