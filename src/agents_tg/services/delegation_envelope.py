"""Formal delegation contract (orchestrator → specialist / plan executor)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DelegationEnvelope:
    task_id: str
    requester_user_id: int
    target_agent_id: str
    initial_prompt: str
    orchestrator_id: str = "orchestrator"
    context_budget: dict[str, int] = field(default_factory=lambda: {"tokens": 2048})
    relevant_context: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    delegation_chain: list[dict[str, Any]] = field(default_factory=list)
    callback_job_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Full serializable envelope for task context_json."""
        return {
            "task_id": self.task_id,
            "requester_user_id": self.requester_user_id,
            "orchestrator_id": self.orchestrator_id,
            "target_agent_id": self.target_agent_id,
            "initial_prompt": self.initial_prompt,
            "context_budget": self.context_budget,
            "relevant_context": self.relevant_context,
            "artifacts": self.artifacts,
            "delegation_chain": self.delegation_chain,
            "callback_job_id": self.callback_job_id,
        }

    def to_context_patch(self) -> dict[str, Any]:
        return {
            "delegation": {
                "task_id": self.task_id,
                "target_agent_id": self.target_agent_id,
                "initial_prompt": self.initial_prompt[:500],
                "chain_len": len(self.delegation_chain),
            }
        }

    @classmethod
    def from_plan_step(
        cls,
        *,
        task_id: str,
        requester_user_id: int,
        target_agent_id: str,
        instruction: str,
        user_text: str = "",
    ) -> DelegationEnvelope:
        chain = [
            {
                "from_agent_id": "orchestrator",
                "to_agent_id": target_agent_id,
            }
        ]
        return cls(
            task_id=task_id,
            requester_user_id=requester_user_id,
            target_agent_id=target_agent_id,
            initial_prompt=instruction,
            relevant_context={"user_text": user_text[:1000]} if user_text else {},
            delegation_chain=chain,
        )
