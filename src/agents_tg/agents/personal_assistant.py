"""Personal Assistant Agent - manages Obsidian, Calendar, and Tasks."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents_tg.config.settings import get_settings
from src.agents_tg.utils.git_sync import obsidian_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class PersonalAssistant:
    """Agent for managing personal life (Obsidian, Tasks, Calendar)."""

    def __init__(self) -> None:
        self.obsidian_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "vault")
        if not os.path.exists(self.obsidian_vault_path):
            os.makedirs(self.obsidian_vault_path)

        self._soul_path = Path(__file__).parent / "souls" / "personal_assistant.md"

        # In-memory storage for tasks/events (will move to DB)
        self.tasks: List[Dict[str, Any]] = []

    def _load_soul(self) -> str:
        if self._soul_path.exists():
            return self._soul_path.read_text(encoding="utf-8")
        return ""

    async def create_obsidian_note(
        self, title: str, content: str, folder: str = "Inbox"
    ) -> str:
        """Create a new note in Obsidian vault and sync."""
        obsidian_sync.pull()

        folder_path = os.path.join(self.obsidian_vault_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, f"{title}.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                f"created: {datetime.now().isoformat()}\n"
                "tags: [ai-assistant]\n"
                "---\n\n"
            )
            f.write(content)

        sync_res = obsidian_sync.sync(f"Create note: {title}")
        suffix = sync_res if "Error" in sync_res else ""
        return f"✅ Заметка '{title}' создана и " f"синхронизирована. {suffix}"

    async def add_task(self, title: str, due_date: Optional[str] = None) -> str:
        """Add a task to ToDo list."""
        task = {
            "title": title,
            "due_date": due_date,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        self.tasks.append(task)
        due_str = due_date or "бессрочно"
        return f"✅ Задача '{title}' добавлена на {due_str}"

    async def list_tasks(self) -> str:
        """List current tasks."""
        if not self.tasks:
            return "📭 Список задач пуст"

        res = "📅 Твои задачи:\n"
        for i, task in enumerate(self.tasks, 1):
            due = task["due_date"] or "нет срока"
            res += f"{i}. {task['title']} ({due})\n"
        return res

    async def process(self, message: str) -> str:
        """Process requests for personal assistant using LLM."""
        from src.agents_tg.services.qwen_client import qwen_client

        soul = self._load_soul()

        prompt = (
            f"{soul}\n\n"
            "Ты - Личный помощник. Проанализируй запрос "
            "пользователя и выбери действие.\n\n"
            "Доступные действия:\n"
            "1. CREATE_NOTE: [Title]: [Content] - создать "
            "заметку в Obsidian.\n"
            "2. ADD_TASK: [Title] - добавить задачу.\n"
            "3. LIST_TASKS - показать список задач.\n"
            "4. CHAT: [Response] - просто ответить "
            "пользователю.\n\n"
            f"Запрос: {message}\n\n"
            "Ответь в формате: ACTION: [Параметры]"
        )

        response = await qwen_client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            agent_key="personal_assistant",
        )

        if "CREATE_NOTE" in response:
            try:
                parts = response.split("CREATE_NOTE:", 1)[1].split(":", 1)
                title = parts[0].strip()
                content = parts[1].strip()
                return await self.create_obsidian_note(title, content)
            except Exception:
                return (
                    "Ошибка при создании заметки. "
                    "Убедись в формате "
                    "'Заголовок: Текст'."
                )

        if "ADD_TASK" in response:
            title = response.split("ADD_TASK:", 1)[1].strip()
            return await self.add_task(title)

        if "LIST_TASKS" in response:
            return await self.list_tasks()

        if "CHAT" in response:
            return response.split("CHAT:", 1)[1].strip()

        return response


# Singleton instance
personal_assistant = PersonalAssistant()
