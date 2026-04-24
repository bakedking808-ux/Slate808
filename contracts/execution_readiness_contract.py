from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExecutionAction = Literal[
    "plan_display",
    "calendar_review",
    "calendar_schedule",
    "booking_prep",
]
ReadinessLevel = Literal[
    "not_plan_ready",
    "plan_ready_only",
    "execution_ready",
]


class ExecutionReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    brief: dict
    planning_constraints: dict | None = None
    plan_status: str | None = None
    requested_action: ExecutionAction | None = None
    calendar_preference: str | None = None


class ExecutionReadinessResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    plan_ready: bool
    execution_ready: bool
    execution_blocked: bool
    readiness_level: ReadinessLevel
    requested_action: ExecutionAction | None = None
    action_allowed: bool | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    allowed_actions: list[ExecutionAction] = Field(default_factory=list)
    blocked_actions: list[ExecutionAction] = Field(default_factory=list)
