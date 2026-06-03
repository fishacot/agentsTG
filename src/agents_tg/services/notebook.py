"""Owner notebook on disk — external memory outside Groq context window."""

from __future__ import annotations

from pathlib import Path

from src.agents_tg.config.settings import get_settings
from src.agents_tg.utils.timezone_utils import now_local


def notebook_path(telegram_user_id: int | str) -> Path:
    settings = get_settings()
    root = settings.ROOT_DIR / "workspace" / "users" / str(telegram_user_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "NOTEBOOK.md"


def load_notebook_block(user_id: str) -> str:
    """Trimmed notebook for system prompt injection."""
    settings = get_settings()
    max_chars = int(getattr(settings, "NOTEBOOK_MAX_CHARS", 1500) or 1500)
    path = notebook_path(user_id)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not text:
        return ""
    clipped = text[-max_chars:] if len(text) > max_chars else text
    return f"## Блокнот владельца (NOTEBOOK.md)\n{clipped}\n"


def append_notebook(
    telegram_user_id: int | str,
    *,
    text: str,
    agent_key: str = "personal_assistant",
) -> dict[str, object]:
    line = (text or "").strip()
    if not line:
        return {"ok": False, "error": "empty_text"}
    path = notebook_path(telegram_user_id)
    stamp = now_local().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{stamp}] **{agent_key}:** {line[:800]}\n"
    if path.exists():
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        path.write_text(
            "# NOTEBOOK — заметки владельца\n\n"
            "_Редактируйте вручную или через append_notebook. "
            "Агенты читают этот файл, не дублируйте всё в чат._\n\n" + entry,
            encoding="utf-8",
        )
    return {"ok": True, "path": str(path.name)}
