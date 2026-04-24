from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from contracts.plan_refinement_contract import PlanRefinementInput, PlanRefinementResult
from engine.planning_policy import validate_planning_constraints


STEP_REFINEMENT_STAGE_ORDER = (
    "weak_context_strengthening",
    "semantic_tail_compaction",
)


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


def _compact_step(step: str) -> str:
    compacted = step
    replacements = [
        (
            "then align bookings and align premium bookings",
            "then align premium bookings",
        ),
        (
            "and align bookings and align premium bookings",
            "and align premium bookings",
        ),
        (
            "and align bookings and align transport and accommodation for the family",
            "and align bookings, transport, and accommodation for the family",
        ),
        (
            "and align bookings and align team logistics efficiently",
            "and align bookings and team logistics efficiently",
        ),
        (
            " with family-friendly, comfortable options",
            " with comfortable family options",
        ),
        (
            "; practical and safe movement",
            "",
        ),
        (
            "; in calm and quieter settings",
            "; in quieter settings",
        ),
    ]

    for old, new in replacements:
        compacted = compacted.replace(old, new)
    return compacted


def _destination_label(destination_policy: dict[str, Any]) -> str:
    destination_type = destination_policy.get("destination_type")
    if destination_type in {"coastal", "safari", "city", "mountain", "lake", "forest", "arid"}:
        return str(destination_type)
    return ""


def _budget_label(budget_policy: dict[str, Any]) -> str:
    budget_posture = budget_policy.get("budget_posture")
    if budget_posture == "cost_sensitive":
        return "cost-conscious"
    if budget_posture == "balanced":
        return "balanced"
    if budget_posture == "premium":
        return "comfort-led"
    return ""


def _traveller_label(traveller_policy: dict[str, Any]) -> str:
    group_type = traveller_policy.get("group_type")
    if traveller_policy.get("needs_family_safe_planning"):
        return "family"
    if group_type == "team":
        return "team"
    if traveller_policy.get("needs_group_coordination"):
        return "group"
    return ""


def _mood_label(mood_policy: dict[str, Any]) -> str:
    trip_mood = mood_policy.get("trip_mood")
    if trip_mood in {"relaxed", "romantic", "adventure", "luxury"}:
        return str(trip_mood)
    if trip_mood == "corporate":
        return "schedule-aware"
    return ""


def _strengthen_weak_step(
    step: str,
    brief: dict[str, Any] | None,
    constraints: dict[str, Any],
) -> str:
    destination = (brief or {}).get("destination")
    destination_label = _destination_label(constraints["destination_policy"])
    budget_label = _budget_label(constraints["budget_policy"])
    traveller_label = _traveller_label(constraints["traveller_policy"])
    mood_label = _mood_label(constraints["mood_policy"])
    timing_summary = constraints["timing_policy"].get("timing_summary")

    if step == "Set a budget and estimate the main costs" and budget_label:
        return f"Set a {budget_label} budget and estimate the main costs"

    if step == "Confirm the trip timing clearly" and timing_summary and timing_summary != "timing not specified":
        group = f" with {traveller_label} schedule coordination" if traveller_label else ""
        mood = f" and a {mood_label} pace" if mood_label else ""
        return f"Confirm the trip timing as {timing_summary}{group}{mood}"

    if not destination:
        return step

    transport_template = "Choose transport and lodging options that fit the trip"
    if step == transport_template or step.startswith(f"{transport_template};"):
        context = f"{destination_label} " if destination_label else ""
        budget = f" with {budget_label} choices" if budget_label else ""
        group = f" for {traveller_label} coordination" if traveller_label else ""
        tail = step.removeprefix(transport_template)
        return f"Choose {context}transport and lodging options for {destination} that fit the trip{budget}{group}{tail}"

    activity_template = "Select activities that match your travel goals"
    if step == activity_template or step.startswith(f"{activity_template} "):
        context = f"{destination_label} " if destination_label else ""
        mood = f"{mood_label} " if mood_label else ""
        group = f" for {traveller_label} needs" if traveller_label else ""
        tail = step.removeprefix(activity_template)
        return f"Select {context}{mood}activities in {destination} that match your travel goals{group}{tail}"

    return step


def _refine_steps(
    steps: list[str],
    brief: dict[str, Any] | None,
    constraints: dict[str, Any],
) -> list[str]:
    return [_refine_step(step, brief, constraints) for step in steps]


def _refine_step(
    step: str,
    brief: dict[str, Any] | None,
    constraints: dict[str, Any],
) -> str:
    refined_step = step
    for stage in STEP_REFINEMENT_STAGE_ORDER:
        if stage == "weak_context_strengthening":
            refined_step = _strengthen_weak_step(refined_step, brief, constraints)
        elif stage == "semantic_tail_compaction":
            refined_step = _compact_step(refined_step)
    return refined_step


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

    original_steps = list(refined.get("steps") or [])
    refined["steps"] = _refine_steps(original_steps, refinement_input.brief, constraints)

    checks = list(refined.get("checks") or [])
    risks = list(refined.get("risks") or [])
    if len(checks) < 4 or len(risks) < 2:
        return PlanRefinementResult(refined_plan=refined).refined_plan

    refined["checks"], refined["risks"] = _trip_refinement(checks, risks, constraints)
    changed_sections = ["checks", "risks"]
    if refined["steps"] != original_steps:
        changed_sections.insert(0, "steps")

    return PlanRefinementResult(
        refined_plan=refined,
        changed_sections=changed_sections,
    ).refined_plan
