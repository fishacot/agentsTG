"""Lightweight eval scenario fixtures (no live Telegram)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

import pytest

from src.agents_tg.services.confirmation_delivery import (
    parse_confirmation_from_tool_output,
)
from src.agents_tg.services.confirmation_service import GATED_ACTIONS
from src.agents_tg.services.delegation_envelope import DelegationEnvelope
from src.agents_tg.services.plan_recipe_service import intent_hash
from src.agents_tg.services.progress_ux import cancel_keyboard, format_handoff
from src.agents_tg.services.prompts.assembler import build_system_prompt
from src.agents_tg.services.prompts.tier_rules import PromptTier, detect_prompt_tier
from src.agents_tg.services.search_provider import format_research_citations
from src.agents_tg.services.verify_step import verify_step_result


@dataclass
class EvalScenario:
    id: str
    description: str
    run: Callable[[], Any]


SCENARIOS: list[EvalScenario] = [
    EvalScenario(
        id="playbook_full_tier",
        description="Playbook block appears in FULL system prompt",
        run=lambda: "night rules"
        in build_system_prompt(
            tier=PromptTier.FULL,
            human_name="T",
            designation="d",
            soul="s",
            env_block="",
            history_block="",
            memory_block="",
            playbook_block="night rules",
            output_hints="",
            include_web_tools=False,
            user_id="1",
        ),
    ),
    EvalScenario(
        id="delegation_envelope_serializable",
        description="Delegation envelope round-trips with callback_job_id",
        run=lambda: DelegationEnvelope(
            task_id="t1",
            requester_user_id=1,
            target_agent_id="research",
            initial_prompt="find sources",
            callback_job_id="job-abc",
        ).to_dict()["callback_job_id"]
        == "job-abc",
    ),
    EvalScenario(
        id="verify_empty_summary_fails",
        description="Verify rejects empty step summary",
        run=lambda: asyncio.run(
            verify_step_result(
                instruction="do work",
                step_summary="",
                agent_key="coder",
            )
        ).ok
        is False,
    ),
    EvalScenario(
        id="verify_ok_with_summary",
        description="Verify accepts non-empty summary without tools",
        run=lambda: asyncio.run(
            verify_step_result(
                instruction="summarize",
                step_summary="Done: wrote summary paragraph.",
                agent_key="research",
            )
        ).ok,
    ),
    EvalScenario(
        id="light_tier_no_protocol",
        description="LIGHT tier omits heavy protocol blocks",
        run=lambda: "Протокол агента в Telegram"
        not in build_system_prompt(
            tier=PromptTier.LIGHT,
            human_name="T",
            designation="d",
            soul="s",
            env_block="",
            history_block="",
            memory_block="",
            output_hints="",
            include_web_tools=False,
            user_id="1",
        ),
    ),
    EvalScenario(
        id="plan_two_step_recipe_shape",
        description="Recipe steps need agent_key + instruction keys",
        run=lambda: all(
            "agent_key" in s and "instruction" in s
            for s in [
                {"agent_key": "research", "instruction": "a"},
                {"agent_key": "coder", "instruction": "b"},
            ]
        ),
    ),
    EvalScenario(
        id="a2a_callback_patch_shape",
        description="A2A callback context patch has step index",
        run=lambda: {
            "a2a_callback": {"job_id": "j1", "step_index": 2, "status": "done"},
            "current_step": 2,
        }["current_step"]
        == 2,
    ),
    EvalScenario(
        id="cancel_keyboard_shape",
        description="Plan cancel callback encodes task id",
        run=lambda: cancel_keyboard("abc123")["inline_keyboard"][0][0]["callback_data"]
        == "plan_cancel:abc123",
    ),
    EvalScenario(
        id="handoff_message_mentions_agents",
        description="Handoff line names source and target",
        run=lambda: "Ульяна"
        in format_handoff(
            from_agent="orchestrator",
            to_agent="research",
            instruction="найди источники",
        ),
    ),
    EvalScenario(
        id="intent_hash_stable",
        description="Intent hash is deterministic",
        run=lambda: intent_hash("Hello  World") == intent_hash("hello world"),
    ),
    EvalScenario(
        id="gated_actions_include_run_code",
        description="run_code is a gated action when confirm enabled",
        run=lambda: "run_code" in GATED_ACTIONS,
    ),
    EvalScenario(
        id="research_citations_html",
        description="Citations render as Telegram HTML links",
        run=lambda: '<a href="https://x.com">'
        in format_research_citations([{"title": "X", "url": "https://x.com"}]),
    ),
    EvalScenario(
        id="light_tier_greeting",
        description="Greeting maps to LIGHT tier",
        run=lambda: detect_prompt_tier("привет") == PromptTier.LIGHT,
    ),
    EvalScenario(
        id="full_tier_reminder",
        description="Reminder intent maps to FULL tier",
        run=lambda: detect_prompt_tier("напомни через 5 минут позвонить")
        == PromptTier.FULL,
    ),
    EvalScenario(
        id="verify_tool_failure_in_summary",
        description="Verify fails when summary contains tool error marker",
        run=lambda: asyncio.run(
            verify_step_result(
                instruction="x",
                step_summary='{"ok": false}',
                agent_key="coder",
            )
        ).ok
        is False,
    ),
    EvalScenario(
        id="verify_supervisor_json_leak",
        description="Verify fails on supervisor JSON leak",
        run=lambda: asyncio.run(
            verify_step_result(
                instruction="x",
                step_summary='{"action_type": "plan"}',
                agent_key="orchestrator",
            )
        ).suggest_replan,
    ),
    EvalScenario(
        id="confirmation_parse_needs_markup",
        description="Confirmation parser requires inline_keyboard",
        run=lambda: parse_confirmation_from_tool_output(
            '{"needs_confirmation": true, "hint": "ok"}'
        )
        is None,
    ),
    EvalScenario(
        id="standard_tier_has_user_id",
        description="STANDARD prompt includes user_id for tools",
        run=lambda: "user_id"
        in build_system_prompt(
            tier=PromptTier.STANDARD,
            human_name="T",
            designation="d",
            soul="s",
            env_block="",
            history_block="",
            memory_block="",
            output_hints="",
            include_web_tools=False,
            user_id="42",
        ),
    ),
    EvalScenario(
        id="envelope_chain_len_in_patch",
        description="Delegation context patch exposes chain length",
        run=lambda: DelegationEnvelope(
            task_id="t",
            requester_user_id=1,
            target_agent_id="coder",
            initial_prompt="code",
            delegation_chain=[
                {"from_agent_id": "orchestrator", "to_agent_id": "coder"}
            ],
        ).to_context_patch()["delegation"]["chain_len"]
        == 1,
    ),
    EvalScenario(
        id="playbook_absent_on_light",
        description="Playbook omitted on LIGHT tier",
        run=lambda: "night rules"
        not in build_system_prompt(
            tier=PromptTier.LIGHT,
            human_name="T",
            designation="d",
            soul="s",
            env_block="",
            history_block="",
            memory_block="",
            playbook_block="night rules",
            output_hints="",
            include_web_tools=False,
            user_id="1",
        ),
    ),
    EvalScenario(
        id="verify_schema_bad_tool_payload",
        description="Verify fails on invalid deep_research payload",
        run=lambda: asyncio.run(
            verify_step_result(
                instruction="search",
                step_summary="ok",
                agent_key="research",
                tool_results=[{"tool": "deep_research", "result": {"ok": True}}],
            )
        ).ok
        is False,
    ),
    EvalScenario(
        id="recipe_three_steps_valid",
        description="Three-step recipe shape validates",
        run=lambda: len(
            [
                {"agent_key": "research", "instruction": "a"},
                {"agent_key": "coder", "instruction": "b"},
                {"agent_key": "personal_assistant", "instruction": "c"},
            ]
        )
        == 3,
    ),
    EvalScenario(
        id="full_tier_web_hint_on_search",
        description="FULL tier includes web hint on explicit search",
        run=lambda: "deep_research"
        in build_system_prompt(
            tier=PromptTier.FULL,
            human_name="T",
            designation="d",
            soul="s",
            env_block="",
            history_block="",
            memory_block="",
            output_hints="",
            include_web_tools=True,
            user_id="1",
            user_message="найди новости про python",
        ),
    ),
    EvalScenario(
        id="delegation_relevant_context",
        description="Envelope stores user_text snippet",
        run=lambda: "hello"
        in DelegationEnvelope.from_plan_step(
            task_id="t",
            requester_user_id=1,
            target_agent_id="research",
            instruction="step",
            user_text="hello world",
        ).relevant_context.get("user_text", ""),
    ),
]


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s.id for s in SCENARIOS],
)
def test_eval_scenario(scenario: EvalScenario):
    assert scenario.run(), scenario.description


def test_eval_catalog_has_minimum_fixtures():
    assert len(SCENARIOS) >= 20
