"""Goal-oriented specialist agents (Manus-style)."""

from __future__ import annotations

from src.agents_tg.services.agent_runner import agent_runner
from src.agents_tg.services.prompts.identity import load_soul
from src.agents_tg.services.prompts.styles.business import BUSINESS_STYLE
from src.agents_tg.services.prompts.styles.coder import CODER_STYLE
from src.agents_tg.services.prompts.styles.marketing import MARKETING_STYLE
from src.agents_tg.services.prompts.styles.research import RESEARCH_STYLE
from src.agents_tg.services.prompts.styles.security import SECURITY_STYLE
from src.agents_tg.services.prompts.styles.specialist import MANUS_SPECIALIST_STYLE

DEFAULT_OUTPUT = (
    "Сформируй полезный ответ по специализации. "
    "Если был deep_research — дай ссылки и следующие шаги."
)

RESEARCH_OUTPUT = (
    "Формат (Telegram HTML):\n"
    "<b>Находки</b> — список ссылок\n"
    "<b>Почему подходит</b>\n"
    "<b>Риски</b>\n"
    "<b>Следующие шаги</b> — 3–7 пунктов"
)

SECURITY_OUTPUT = (
    "Формат HTML: <b>Риски</b> (Severity), <b>Рекомендации</b>, <b>Чеклист</b>. "
    "Без инструкций для вредоносных действий. Без юридических вердиктов."
)

BUSINESS_OUTPUT = (
    "Формат HTML: <b>Цель</b>, <b>Гипотезы</b>, <b>План MVP</b>, <b>Риски</b>. "
    "Бюджет 0."
)

MARKETING_OUTPUT = (
    "Формат HTML: <b>Позиционирование</b>, <b>ЦА</b>, <b>УТП</b>, "
    "<b>Контент</b>, <b>Каналы</b>."
)

CODER_OUTPUT = (
    "Формат HTML: <b>Резюме</b>, <b>Архитектура</b>, <code>код</code> в <pre> если уместно, "
    "<b>Edge cases</b>. План правок — не выполняй сам."
)

ROLE_STYLES: dict[str, str] = {
    "research": RESEARCH_STYLE,
    "security_ai": SECURITY_STYLE,
    "coder": CODER_STYLE,
    "business_manager": BUSINESS_STYLE,
    "marketing": MARKETING_STYLE,
}


class GoalOrientedAgent:
    """Specialist agent: natural dialogue + deep_research when needed."""

    def __init__(
        self,
        agent_key: str,
        soul_file: str | None = None,
        output_hints: str = DEFAULT_OUTPUT,
        role_style: str | None = None,
    ) -> None:
        self.agent_key = agent_key
        self.soul_file = soul_file
        self.output_hints = output_hints
        self.role_style = role_style or MANUS_SPECIALIST_STYLE

    def _load_soul(self) -> str:
        return load_soul(self.agent_key, soul_file=self.soul_file)

    async def process(
        self,
        user_message: str,
        user_id: str = "default",
        environment=None,
        environment_block: str = "",
    ) -> str:
        from src.agents_tg.services.environment_context import AgentEnvironment

        env = environment if isinstance(environment, AgentEnvironment) else None
        hints = f"{self.role_style}\n\n{self.output_hints}"
        return await agent_runner.run(
            agent_key=self.agent_key,
            soul=self._load_soul(),
            user_message=user_message,
            user_id=user_id,
            output_hints=hints,
            include_web_tools=True,
            environment=env,
            environment_block=environment_block,
            temperature=0.35,
            max_tokens=768,
        )


research_analyst = GoalOrientedAgent(
    agent_key="research",
    role_style=RESEARCH_STYLE,
    output_hints=RESEARCH_OUTPUT,
)
security_ai = GoalOrientedAgent(
    agent_key="security_ai",
    soul_file="security_ai.md",
    role_style=SECURITY_STYLE,
    output_hints=SECURITY_OUTPUT,
)
business_manager = GoalOrientedAgent(
    agent_key="business_manager",
    soul_file="business_manager.md",
    role_style=BUSINESS_STYLE,
    output_hints=BUSINESS_OUTPUT,
)
marketing = GoalOrientedAgent(
    agent_key="marketing",
    soul_file="marketing.md",
    role_style=MARKETING_STYLE,
    output_hints=MARKETING_OUTPUT,
)
general = GoalOrientedAgent(
    agent_key="general",
    soul_file="general.md",
    output_hints=DEFAULT_OUTPUT,
)
coder = GoalOrientedAgent(
    agent_key="coder",
    soul_file="coder_soul.md",
    role_style=CODER_STYLE,
    output_hints=CODER_OUTPUT,
)

__all__ = [
    "GoalOrientedAgent",
    "ROLE_STYLES",
    "business_manager",
    "coder",
    "general",
    "marketing",
    "research_analyst",
    "security_ai",
]
