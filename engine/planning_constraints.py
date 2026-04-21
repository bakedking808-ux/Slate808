from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from engine.constraints import ConstraintPolicy


class GlobalFlagsModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    constraints: list[str] = Field(default_factory=list)
    is_budget_constrained: bool
    is_group_sensitive: bool
    is_timing_strong: bool
    requires_safe_activity_filter: bool
    requires_coordination_bias: bool
    conflict_flags: list[str] = Field(default_factory=list)
    resolved_constraints: list[str] = Field(default_factory=list)
    refinement_flags: list[str] = Field(default_factory=list)


class PlanningConstraints(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    destination_policy: dict[str, Any]
    budget_policy: dict[str, Any]
    traveller_policy: dict[str, Any]
    mood_policy: dict[str, Any]
    timing_policy: dict[str, Any]
    constraint_policy: ConstraintPolicy
    global_flags: GlobalFlagsModel
