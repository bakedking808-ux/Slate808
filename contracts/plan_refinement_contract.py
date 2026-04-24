from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanRefinementInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    plan: dict[str, Any]
    brief: dict[str, Any] | None = None
    planning_constraints: dict[str, Any] | None = None


class PlanRefinementResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    refined_plan: dict[str, Any]
    changed_sections: list[str] = Field(default_factory=list)
