from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from contracts.plan_refinement_contract import PlanRefinementInput, PlanRefinementResult
from engine.planning_policy import validate_planning_constraints


def _validated_constraints(planning_constraints: dict[str, Any] | None) -> dict[str, Any] | None:
    if not planning_constraints:
        return None
    try:
        return validate_planning_constraints(planning_constraints).model_dump()
    except ValidationError:
        return None


def _trip_refinement(checks: list[str], risks: list[str], constraints: dict[str, Any]) -> tuple[list[str], list[str]]:
    budget = constraints["budget_policy"]
    traveller = constraints["traveller_policy"]
    timing = constraints["timing_policy"]

    if budget.get("should_require_cost_check"):
        checks[1] = "Costs should be checked against the stated budget before booking"
        risks[0] = "Costs may drift if transport, lodging, and activities are not priced together"
    if traveller.get("needs_family_safe_planning"):
        checks[2] = "Activities should remain family-safe, practical, and well-paced for the group"
        risks[1] = "The plan may become too complex if family-safe pacing is not preserved"
    if timing.get("should_treat_as_provisional"):
        checks[3] = "Timing should remain provisional until exact dates are confirmed"
        risks[1] = "Bookings may be premature until exact travel dates are confirmed"

    return checks, risks


def refine_plan(
    plan: dict[str, Any],
    brief: dict[str, Any] | None = None,
    planning_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    refinement_input = PlanRefinementInput(
        plan=plan,
        brief=brief or plan.get("brief"),
        planning_constraints=planning_constraints or plan.get("planning_constraints"),
    )
    refined = deepcopy(refinement_input.plan)

    constraints = _validated_constraints(refinement_input.planning_constraints)
    if refined.get("task_type") != "trip" or constraints is None:
        return PlanRefinementResult(refined_plan=refined).refined_plan

    checks = list(refined.get("checks") or [])
    risks = list(refined.get("risks") or [])
    if len(checks) < 4 or len(risks) < 2:
        return PlanRefinementResult(refined_plan=refined).refined_plan

    refined["checks"], refined["risks"] = _trip_refinement(checks, risks, constraints)
    return PlanRefinementResult(
        refined_plan=refined,
        changed_sections=["checks", "risks"],
    ).refined_plan
