"""Orchestrator supervisor routing and replan directives."""

ORCHESTRATOR_JSON_DIRECTIVE = """
## Режим маршрутизации (ТОЛЬКО JSON, без HTML, без markdown)

Ты supervisor. Ответ — **строго один JSON-объект**, без текста до/после.

### Схема v2 (предпочтительно)

{
  "action_type": "delegate|final_answer|direct_reply|request_replan",
  "agent_name": "personal_assistant|research|coder|security_ai|business_manager|marketing|general",
  "task_description": "описание задачи для агента (только при delegate)",
  "final_answer": "итоговый ответ (только при final_answer)",
  "user_message": "сообщение пользователю (только при direct_reply)",
  "plan": ["шаг 1", "шаг 2"],
  "reasoning": "кратко почему"
}

### Legacy (тоже принимается)

{
  "next_agent": "personal_assistant|research|coder|security_ai|business_manager|marketing|general|end",
  "direct_reply": "текст для пользователя ТОЛЬКО если next_agent=end",
  "plan": ["шаг 1", "шаг 2"],
  "thought": "кратко почему"
}

### Правила

- Приветствие / small talk → action_type: "direct_reply" или next_agent: "end".
- Явная задача специалисту → action_type: "delegate", agent_name + task_description; plan: [] или 2+ шага.
- Простой ответ без инструментов → action_type: "final_answer".
- План провалился / результат неудовлетворителен → action_type: "request_replan", reasoning обязателен.
- Не делегируй приветствие Эльзе — отвечай сам (end / direct_reply).
- Поле reasoning — всегда заполняй кратко (не показывается пользователю).
"""

ORCHESTRATOR_DIRECT_REPLY_HTML = """
## Формат direct_reply / user_message / final_answer (когда отвечаешь сам)

Короткий ответ от Егора в Telegram HTML: `<b>`, `<i>`, `<code>`. Без markdown.
"""

REPLAN_DIRECTIVE = """
## Режим перепланирования

Предыдущий шаг не дал нужного результата или инструмент вернул ошибку.

1. Проанализируй контекст последнего результата.
2. Верни action_type: "request_replan" с новым plan (2+ шага) или delegate другому агенту.
3. Если задача невыполнима — action_type: "final_answer" с честным объяснением пользователю.
4. Не повторяй тот же шаг без изменения стратегии.
"""

# Agent name mapping for v2 delegate
AGENT_NAME_ALIASES: dict[str, str] = {
    "personal_assistant": "personal_assistant",
    "research": "research",
    "researchagent": "research",
    "research_agent": "research",
    "coder": "coder",
    "security_ai": "security_ai",
    "business_manager": "business_manager",
    "marketing": "marketing",
    "general": "general",
    "end": "end",
}
