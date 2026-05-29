import logging
from pathlib import Path

from src.agents_tg.services.agent_runner import agent_runner

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = (
    "Сформируй полезный ответ по своей специализации. "
    "Если использовал поиск — дай ссылки и следующие шаги."
)

RESEARCH_OUTPUT = (
    "Формат ответа:\n"
    "- Находки со ссылками\n"
    "- Почему подходит\n"
    "- Риски\n"
    "- Следующие шаги (3–7 пунктов)"
)

SECURITY_OUTPUT = (
    "Формат: риски (Severity), рекомендации, чеклист проверок. "
    "Не давай инструкций для вредоносных действий."
)

BUSINESS_OUTPUT = (
    "Формат: цель, гипотезы, план MVP, риски. Учитывай бюджет 0."
)

MARKETING_OUTPUT = (
    "Формат: позиционирование, ЦА, УТП, идеи контента, каналы роста."
)

CODER_OUTPUT = (
    "Формат: резюме проблемы, архитектура/подход, пример кода если уместно, "
    "подводные камни. Опиши план правок, не выполняй их сам."
)


class GoalOrientedAgent:
    """Specialist agent: natural dialogue + web tools when the goal requires them."""

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

    async def process(self, user_message: str, user_id: str = "default") -> str:
        return await agent_runner.run(
            agent_key=self.agent_key,
            soul=self._load_soul(),
            user_message=user_message,
            user_id=user_id,
            output_hints=self.output_hints,
            include_web_tools=True,
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
