"""Orchestrator Agent using LangGraph for multi-agent coordination."""

import json
import logging
from pathlib import Path
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from src.agents_tg.agents.specialists import (
    business_manager,
    coder,
    general,
    marketing,
    research_analyst,
    security_ai,
)
from src.agents_tg.services.memory_service import memory_service
from src.agents_tg.services.qwen_client import qwen_client

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """The state of the orchestration graph."""

    messages: Annotated[List[BaseMessage], add_messages]
    next_agent: str
    user_id: str
    plan: List[str]
    current_step: int


ORCHESTRATOR_SYSTEM_PROMPT = (
    "Ты - Оркестратор мультиагентной системы.\n"
    "Твоя задача - проанализировать запрос пользователя, "
    "составить план действий и делегировать задачи.\n\n"
    "ФИЛОСОФИЯ (Mens et Manus):\n"
    "Мы не просто отвечаем на вопросы, мы ДОСТАВЛЯЕМ результат. "
    "Если пользователь просит информацию - мы создаем заметку. "
    "Если просит проект - мы ищем ресурсы и составляем план.\n\n"
    "ТВОЙ АЛГОРИТМ:\n"
    "1. Пойми намерение пользователя.\n"
    "2. Составь краткий план (Plan) из 2-3 шагов.\n"
    "3. Выбери первого агента для выполнения шага 1.\n\n"
    "Доступные агенты (специалисты):\n"
    "1. **personal_assistant** - управление временем, задачи, "
    "заметки в Obsidian, календарь, лёгкий личный бюджет.\n"
    "2. **research** - ресерч и аналитика: найти репозитории, "
    "best practices, конкурентов, собрать выжимку.\n"
    "3. **coder** - код, архитектура, ревью, подсказки по реализации.\n"
    "4. **security_ai** - безопасность ИИ, уязвимости LLM, "
    "безопасная архитектура, помощь в кодинге.\n"
    "5. **business_manager** - проекты, бизнес-идеи, продукт, "
    "приоритизация, риски, план запуска.\n"
    "6. **marketing** - маркетинг, позиционирование, тональность, "
    "контент, рост аудитории.\n\n"
    "ФОРМАТ ОТВЕТА (строго JSON):\n"
    '{\n  "plan": ["шаг 1", "шаг 2"],\n'
    '  "next_agent": "имя_агента",\n'
    '  "thought": "почему выбран этот агент"\n}\n\n'
    'Если задача выполнена, напиши "next_agent": "end".'
)


class Orchestrator:
    """Orchestrator that manages multi-agent interactions using LangGraph."""

    def __init__(self) -> None:
        self.souls_path = Path(__file__).parent / "souls"
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _load_soul(self, agent_name: str) -> str:
        """Load SOUL.md for a specific agent."""
        soul_file = self.souls_path / f"{agent_name}.md"
        if soul_file.exists():
            return soul_file.read_text(encoding="utf-8")
        logger.warning("SOUL file for %s not found.", agent_name)
        return ""

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("personal_assistant", self.personal_assistant_node)
        workflow.add_node("research", self.research_node)
        workflow.add_node("coder", self.coder_node)
        workflow.add_node("security_ai", self.security_ai_node)
        workflow.add_node("business_manager", self.business_manager_node)
        workflow.add_node("marketing", self.marketing_node)
        workflow.add_node("general", self.general_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self.router,
            {
                "personal_assistant": "personal_assistant",
                "research": "research",
                "coder": "coder",
                "security_ai": "security_ai",
                "business_manager": "business_manager",
                "marketing": "marketing",
                "general": "general",
                "end": END,
            },
        )

        workflow.add_edge("personal_assistant", "supervisor")
        workflow.add_edge("research", "supervisor")
        workflow.add_edge("coder", "supervisor")
        workflow.add_edge("security_ai", "supervisor")
        workflow.add_edge("business_manager", "supervisor")
        workflow.add_edge("marketing", "supervisor")
        workflow.add_edge("general", END)

        return workflow

    async def supervisor_node(self, state: AgentState) -> Dict[str, Any]:
        """Node that decides which agent to call next and manages the plan."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        orchestrator_soul = self._load_soul("orchestrator")

        memories = await memory_service.search(last_message, user_id=user_id)
        memory_context = ""
        if memories:
            memory_lines = "\n".join([f"- {m['text']}" for m in memories])
            memory_context = f"\n\nРЕКОРДЫ ПАМЯТИ (Mem0):\n{memory_lines}"

        messages = [
            {
                "role": "system",
                "content": (
                    f"{orchestrator_soul}{memory_context}\n\n"
                    f"{ORCHESTRATOR_SYSTEM_PROMPT}"
                ),
            },
            {"role": "user", "content": last_message},
        ]

        if state.get("plan"):
            steps = "\n".join(
                [f"{i+1}. {step}" for i, step in enumerate(state["plan"])]
            )
            plan_status = (
                "СУЩЕСТВУЮЩИЙ ПЛАН ДЛЯ ЭТОГО ЗАПРОСА:\n"
                f"{steps}\n\n"
                f"Текущий шаг: {state['current_step']}"
            )
            messages.append({"role": "assistant", "content": plan_status})

        response = await qwen_client.chat(messages, temperature=0.1)

        try:
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = (
                    clean_response.split("```json")[1].split("```")[0].strip()
                )

            data = json.loads(clean_response)
            next_agent = data.get("next_agent", "general")
            plan = data.get("plan", state.get("plan", []))

            return {
                "next_agent": next_agent,
                "plan": plan,
                "current_step": state.get("current_step", 0) + 1,
            }
        except Exception as e:
            logger.error(
                "Error parsing supervisor response: %s. Raw: %s",
                e,
                response,
            )
            return {
                "next_agent": "general",
                "plan": ["Обработать запрос"],
                "current_step": 1,
            }

    def router(self, state: AgentState) -> str:
        """Routing logic based on next_agent state."""
        return state["next_agent"]

    async def personal_assistant_node(self, state: AgentState) -> Dict[str, Any]:
        """Personal Assistant agent node."""
        from src.agents_tg.agents.personal_assistant import (
            personal_assistant,
        )

        last_message = state["messages"][-1].content
        response = await personal_assistant.process(last_message)
        return {"messages": [HumanMessage(content=response, name="personal_assistant")]}

    async def research_node(self, state: AgentState) -> Dict[str, Any]:
        """Research / Intel agent node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await research_analyst.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="research")]}

    async def coder_node(self, state: AgentState) -> Dict[str, Any]:
        """Coder / Architect agent node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await coder.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="coder")]}

    async def security_ai_node(self, state: AgentState) -> Dict[str, Any]:
        """Security AI agent node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await security_ai.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="security_ai")]}

    async def business_manager_node(self, state: AgentState) -> Dict[str, Any]:
        """Business Manager agent node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await business_manager.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="business_manager")]}

    async def marketing_node(self, state: AgentState) -> Dict[str, Any]:
        """Marketing agent node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await marketing.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="marketing")]}

    async def general_node(self, state: AgentState) -> Dict[str, Any]:
        """General chat node."""
        last_message = state["messages"][-1].content
        user_id = state.get("user_id", "default")
        response = await general.process(last_message, user_id=user_id)
        return {"messages": [HumanMessage(content=response, name="general")]}

    async def process(self, message: str, user_id: str = "default") -> str:
        """Process a message through the graph."""
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "next_agent": "",
            "plan": [],
            "current_step": 0,
        }

        final_state = await self.app.ainvoke(initial_state)

        plan_str = ""
        if final_state.get("plan"):
            steps = "\n".join(
                [f"{i+1}. {step}" for i, step in enumerate(final_state["plan"])]
            )
            plan_str = f"📋 **План действий:**\n{steps}\n\n"

        if final_state["messages"]:
            return f"{plan_str}{final_state['messages'][-1].content}"
        return "Извини, я не смог обработать твой запрос."


# Singleton instance
orchestrator = Orchestrator()
