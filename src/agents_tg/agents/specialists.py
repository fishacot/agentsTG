import logging
from pathlib import Path

from src.agents_tg.services.agent_runner import agent_runner

logger = logging.getLogger(__name__)

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


class GoalOrientedAgent:
    """Specialist agent: natural dialogue + deep_research when needed."""

    def __init__(
        self,
        agent_key: str,
        soul_file: str,
        output_hints: str = DEFAULT_OUTPUT,
    ) -> None:
        self.agent_key = agent_key
        self.soul_path = Path(__file__).parent / "souls" / soul_file
        self.output_hints = output_hints

    def _load_soul(self) -> str:
        if self.soul_path.exists():
            return self.soul_path.read_text(encoding="utf-8")
        return ""

    async def process(
        self,
        user_message: str,
        user_id: str = "default",
        environment=None,
        environment_block: str = "",
    ) -> str:
        from src.agents_tg.services.environment_context import AgentEnvironment

        env = environment if isinstance(environment, AgentEnvironment) else None
        return await agent_runner.run(
            agent_key=self.agent_key,
            soul=self._load_soul(),
            user_message=user_message,
            user_id=user_id,
            output_hints=self.output_hints,
            include_web_tools=True,
            environment=env,
            environment_block=environment_block,
            temperature=0.35,
        )


research_analyst = GoalOrientedAgent(
    agent_key="research",
    soul_file="sports_analyst.md",
    output_hints=RESEARCH_OUTPUT,
)
security_ai = GoalOrientedAgent(
    agent_key="security_ai",
    soul_file="security_ai.md",
    output_hints=SECURITY_OUTPUT,
)
business_manager = GoalOrientedAgent(
    agent_key="business_manager",
    soul_file="business_manager.md",
    output_hints=BUSINESS_OUTPUT,
)
marketing = GoalOrientedAgent(
    agent_key="marketing",
    soul_file="marketing.md",
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
    output_hints=CODER_OUTPUT,
)
