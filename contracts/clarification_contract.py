from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from planning_policy import PlanningDecision


class ClarificationResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    status: Literal["needs_clarification", "ready"]
    question: str | None
    missing_fields: list[str] = Field(default_factory=list)
    safe_to_proceed: bool


def build_clarification_response(
    decision: PlanningDecision,
) -> ClarificationResponse:
    if decision.action == "clarify":
        return ClarificationResponse(
            status="needs_clarification",
            question=decision.next_question,
            missing_fields=list(decision.missing_fields),
            safe_to_proceed=False,
        )

    if decision.action == "proceed":
        return ClarificationResponse(
            status="ready",
            question=None,
            missing_fields=list(decision.missing_fields),
            safe_to_proceed=True,
        )

    raise ValueError(f"Unsupported planning action: {decision.action}")
