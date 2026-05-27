import json
import logging
from pathlib import Path
from typing import List

from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.qwen_client import qwen_client
from src.agents_tg.utils.internet import fetch_web_page, web_search

logger = logging.getLogger(__name__)


class ToolEnabledAgent:
    def __init__(self, agent_key: str, soul_file: str) -> None:
        self.agent_key = agent_key
        self.soul_path = Path(__file__).parent / "souls" / soul_file

    def _load_soul(self) -> str:
        if self.soul_path.exists():
            return self.soul_path.read_text(encoding="utf-8")
        return ""

    async def _memory_context(self, user_message: str, user_id: str) -> str:
        memories = await memory_service.search(user_message, user_id=user_id)
        if not memories:
            return ""
        lines: List[str] = []
        for m in memories:
            text = m.get("text")
            if text:
                lines.append(f"- {text}")
        if not lines:
            return ""
        return "\n\nПАМЯТЬ ОБ ЭТОМ ПОЛЬЗОВАТЕЛЕ:\n" + "\n".join(lines)

    async def _tool_intent(
        self,
        soul: str,
        memory_ctx: str,
        user_message: str,
    ) -> str:
        prompt = (
            f"{soul}{memory_ctx}\n\n"
            f"Ты - {self.agent_key}. "
            f"Запрос пользователя: {user_message}\n\n"
            "Определи, нужен ли интернет.\n"
            "Ответ строго одним вариантом:\n"
            "NO\n"
            "SEARCH: <поисковый запрос>\n"
            "FETCH: <url>\n"
        )
        return await qwen_client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
        )

    async def _gather_context(self, tool_intent: str) -> str:
        intent = tool_intent.strip()
        if intent.startswith("SEARCH:"):
            query = intent.split("SEARCH:", 1)[1].strip()
            results = await web_search(query, max_results=5)
            if not results:
                return ""
            compact = []
            for r in results:
                title = r.get("title") or ""
                href = r.get("href") or r.get("url") or ""
                body = (r.get("body") or "").strip()
                compact.append(
                    {
                        "title": title,
                        "url": href,
                        "snippet": body[:280],
                    }
                )
            return "WEB_SEARCH_RESULTS_JSON:\n" + json.dumps(
                compact, ensure_ascii=False, indent=2
            )

        if intent.startswith("FETCH:"):
            url = intent.split("FETCH:", 1)[1].strip()
            content = await fetch_web_page(url)
            if not content or content.startswith("Failed"):
                return ""
            return f"WEB_PAGE_CONTENT ({url}):\n{content[:3000]}"

        return ""

    async def _final_answer(
        self,
        soul: str,
        memory_ctx: str,
        user_message: str,
        web_ctx: str,
        output_contract: str,
    ) -> str:
        prompt = (
            f"{soul}{memory_ctx}\n\n"
            f"Запрос пользователя:\n{user_message}\n\n"
            f"{web_ctx}\n\n"
            f"{output_contract}\n"
        )
        return await qwen_client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ.\n"
                "Требования:\n"
                "- Если были результаты поиска: приведи 5-10 "
                "ссылок и кратко объясни, чем полезна каждая.\n"
                "- Дай 3-7 конкретных шагов, "
                "что делать дальше.\n"
                "- Если в данных есть неопределенность: "
                "перечисли, что именно проверить.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


class ResearchAnalyst(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="research",
            soul_file="sports_analyst.md",
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        """Process research queries with a research-focused output contract."""
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ как прикладной ресерчер.\n"
                "Формат:\n"
                "- Находки: список 5–10 ссылок с краткими пояснениями, "
                "чем полезен каждый ресурс.\n"
                "- Почему это подходит: 3–5 пунктов с критериями отбора.\n"
                "- Риски/ограничения: 3–7 пунктов.\n"
                "- Следующие шаги: 3–7 конкретных действий для пользователя.\n"
                "Если данных мало или они противоречивы — явно укажи, что нужно "
                "дополнительно проверить.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


class SecurityAI(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="security_ai",
            soul_file="security_ai.md",
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ как инженер по безопасности.\n"
                "Формат:\n"
                "- Риски (3-8 пунктов, "
                "Severity: low/medium/high)\n"
                "- Рекомендации (конкретные меры)\n"
                "- Что проверить (чеклист)\n"
                "Запрет: не давай инструкций "
                "для вредоносных действий.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


class BusinessManager(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="business_manager",
            soul_file="business_manager.md",
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ как менеджер проектов "
                "и бизнес-стратег.\n"
                "Формат:\n"
                "- Цель (1 строка)\n"
                "- Гипотезы (2-5)\n"
                "- План MVP (5-10 шагов)\n"
                "- Риски и обходные пути\n"
                "- Репозитории/референсы "
                "(если были найдены)\n"
                "Учитывай бюджет 0.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


class Marketing(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="marketing",
            soul_file="marketing.md",
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ как маркетолог.\n"
                "Формат:\n"
                "- Позиционирование (1 абзац)\n"
                "- ЦА (3 сегмента)\n"
                "- УТП (3 варианта)\n"
                "- Контент-план на 7 дней (коротко)\n"
                "- Каналы роста (5 вариантов) + почему\n"
                "Учитывай бюджет 0.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


class General(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="general",
            soul_file="general.md",
        )


class Coder(ToolEnabledAgent):
    def __init__(self) -> None:
        super().__init__(
            agent_key="coder",
            soul_file="coder_soul.md",
        )

    async def process(self, user_message: str, user_id: str = "default") -> str:
        """Process coding and architecture requests as senior Coder/Architect."""
        soul = self._load_soul()
        memory_ctx = await self._memory_context(user_message, user_id=user_id)
        tool_intent = await self._tool_intent(soul, memory_ctx, user_message)
        web_ctx = await self._gather_context(tool_intent)
        answer = await self._final_answer(
            soul=soul,
            memory_ctx=memory_ctx,
            user_message=user_message,
            web_ctx=web_ctx,
            output_contract=(
                "Сформируй ответ как senior-разработчик и архитектор.\n"
                "Формат:\n"
                "- Краткое резюме проблемы (1 абзац).\n"
                "- Предлагаемая архитектура / подход (3–7 пунктов).\n"
                "- Пример кода или diff, если уместно (без лишнего шума).\n"
                "- Потенциальные подводные камни и что проверить.\n"
                "Если требуется правка существующего репозитория, "
                "опиши пошаговый план изменений, а не выполняй их сам.\n"
            ),
        )

        if len(user_message.strip()) >= 12:
            await memory_service.add(user_message.strip(), user_id=user_id)

        return answer


research_analyst = ResearchAnalyst()
security_ai = SecurityAI()
business_manager = BusinessManager()
marketing = Marketing()
general = General()
coder = Coder()
