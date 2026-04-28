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


def _destination_risk_detail(risk_flags: list[str]) -> tuple[str, str] | None:
    risk_rules = [
        (
            "traffic",
            "Transfer timing should include congestion-aware buffers",
            "Traffic can disrupt the plan if movement windows are not buffered",
        ),
        (
            "boat_transfer",
            "Boat-transfer timing should be coordinated before bookings are locked",
            "Boat connections can disrupt arrival or departure timing if left loose",
        ),
        (
            "early_start",
            "Early-start activities should be aligned with transport and rest timing",
            "Early excursions can fail if pickup times and rest windows are not coordinated",
        ),
        (
            "remote_access",
            "Remote-access logistics should be confirmed before committing to the route",
            "Remote access can fail if route certainty and support logistics are weak",
        ),
        (
            "rough_access",
            "Road-condition buffers should be built into transfers",
            "Rough access can disrupt timing if transfer buffers are too tight",
        ),
        (
            "altitude",
            "Arrival-day pacing should stay conservative",
            "Altitude can make an overloaded arrival day harder to manage",
        ),
        (
            "heat",
            "Movement and activity timing should account for heat exposure",
            "Heat can make transfers and activities harder if pacing is too tight",
        ),
    ]

    for flag, check, risk in risk_rules:
        if flag in risk_flags:
            return check, risk
    return None


def _destination_pacing_suffix(destination_policy: dict[str, Any]) -> str:
    risk_flags = destination_policy.get("risk_flags") or []
    pace_bias = destination_policy.get("pace_bias")
    destination_type = destination_policy.get("destination_type")

    if "traffic" in risk_flags:
        return "with transfer buffers for traffic-aware movement"
    if "remote_access" in risk_flags:
        return "with conservative remote-access timing"
    if destination_type == "arid" and ("distance" in risk_flags or pace_bias == "rugged"):
        return "with daylight-aware movement windows"
    if "rough_access" in risk_flags or "distance" in risk_flags:
        return "with drive-time buffers for access conditions"
    if "altitude" in risk_flags or pace_bias == "active":
        return "with conservative arrival-day pacing"
    if "heat" in risk_flags:
        return "with heat-aware pacing and rest windows"
    if pace_bias == "early_start":
        return "with early movement windows aligned"
    return ""


OPERATIONAL_CHECK_LABELS = (
    "Plan Integrity",
    "Travel Documents",
    "Transport & Stay",
    "Budget & Payments",
    "Safety & Local Conditions",
    "Supplier Readiness",
    "Activity Readiness",
)


def _default_operational_checks() -> list[str]:
    return [
        "Plan Integrity: Confirm destination, traveller count, timing, budget, and trip mood remain consistent across the Travel Brief and Plan Steps.",
        "Travel Documents: Confirm guest identification, booking names, and any passport, visa, entry, health, or insurance requirements before booking.",
        "Transport & Stay: Confirm transport availability, route feasibility, accommodation availability, room setup, check-in window, and cancellation terms before locking the plan.",
        "Budget & Payments: Confirm the plan aligns with the stated budget, including hidden costs, peak-season surcharges, refund terms, and secure payment channels.",
        "Safety & Local Conditions: Review destination safety, weather, road conditions, local regulations, emergency contacts, and local support before final confirmation.",
        "Supplier Readiness: Verify supplier reliability, availability, cancellation terms, refund terms, payment instructions, local support, and backup options before booking.",
        "Activity Readiness: Verify activity feasibility, access requirements, age suitability, weather sensitivity, available time, and backup options before final confirmation.",
    ]


def _default_operational_risks() -> list[str]:
    return [
        "Plan Integrity Risk: Missing information, contradictions, or mismatched brief details can weaken the plan before handoff.",
        "Availability Pressure: Transport, stay, and activity options may narrow if availability is not checked early.",
        "Budget Stretch: Hidden costs, peak-season surcharges, or unclear payment terms can push the trip beyond the intended budget.",
        "Safety Exposure: Weather, road conditions, local rules, or weak emergency support can increase travel friction.",
        "Supplier Reliability Risk: Weak supplier verification can expose the trip to failed bookings, poor communication, payment errors, or limited recovery options.",
        "Activity Constraint Risk: Unchecked activity access, age limits, weather sensitivity, or weak pacing can cause cancellations, guest fatigue, or unsuitable experiences.",
    ]


def _has_operational_check_categories(checks: list[str]) -> bool:
    return all(
        any(check.startswith(f"{label}:") for check in checks)
        for label in OPERATIONAL_CHECK_LABELS
    )


def _replace_check(checks: list[str], label: str, value: str) -> list[str]:
    prefix = f"{label}:"
    for index, check in enumerate(checks):
        if check.startswith(prefix):
            checks[index] = value
            return checks
    checks.append(value)
    return checks


def _trip_refinement(checks: list[str], risks: list[str], constraints: dict[str, Any]) -> tuple[list[str], list[str]]:
    budget = constraints["budget_policy"]
    traveller = constraints["traveller_policy"]
    timing = constraints["timing_policy"]
    destination = constraints["destination_policy"]

    if budget.get("should_require_cost_check"):
        checks = _replace_check(
            checks,
            "Budget & Payments",
            "Budget & Payments: Confirm stated costs across transport, stay, activities, hidden fees, refund terms, and secure payment channels before booking.",
        )
        risks[0] = "Budget Stretch: Costs may drift if transport, lodging, activities, and payment terms are not priced together."

    if constraints["constraint_policy"].get("avoid_premium"):
        checks = [
            check.replace("premium trip", "practical trip").replace("Premium", "Practical").replace("premium", "practical")
            for check in checks
        ]
        risks = [risk.replace("Premium", "Practical").replace("premium", "practical") for risk in risks]

    if traveller.get("needs_family_safe_planning"):
        checks = _replace_check(
            checks,
            "Plan Integrity",
            "Plan Integrity: Confirm the family traveller count, child suitability, pacing, and comfort needs remain consistent across the Travel Brief and Plan Steps.",
        )
        risks[1] = "Plan Integrity Risk: The plan may become too complex if family-safe pacing and child suitability are not preserved."

    if timing.get("should_treat_as_provisional"):
        checks = _replace_check(
            checks,
            "Transport & Stay",
            "Transport & Stay: Keep transport, accommodation, and transfer decisions provisional until exact travel dates are confirmed.",
        )
        risks[1] = "Availability Pressure: Bookings may be premature until exact travel dates are confirmed."

    risk_detail = _destination_risk_detail(destination.get("risk_flags") or [])
    if risk_detail:
        checks = _replace_check(
            checks,
            "Safety & Local Conditions",
            f"Safety & Local Conditions: {risk_detail[0]}",
        )
        if risk_detail[1] not in risks:
            risks.append(risk_detail[1])

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
        (
            "family-friendly and comfortable options; safe and practical choices",
            "family-friendly, comfortable, and practical options",
        ),
        (
            "family-friendly and comfortable options; calm, practical choices",
            "family-friendly, comfortable, and practical options",
        ),
        (
            "safe and practical choices",
            "calm, practical choices",
        ),
        (
            "fewer activities and more recovery time; lighter arrival-day and recovery-aware family pacing",
            "fewer activities, lighter arrival-day pacing, and recovery-aware family time",
        ),
        (
            "; confirming the shared schedule for the group",
            "; shared schedule confirmed for the group",
        ),
        (
            "while confirming the shared schedule for the group with departure margin",
            "with shared schedule confirmed and departure margin",
        ),
        (
            "while confirming the shared schedule for the group with departure transfer margin",
            "with shared schedule confirmed and departure margin",
        ),
        (
            "and align transport and accommodation and reserve time for active excursions",
            "and align transport and accommodation while reserving time for active excursions",
        ),
        (
            "with departure transfer margin with drive-time buffers for access conditions",
            "with departure and drive-time buffers for access conditions",
        ),
        (
            "with departure transfer margin with conservative remote-access timing",
            "with departure margin and conservative remote-access timing",
        ),
        (
            "with shared schedule confirmed and departure margin with conservative remote-access timing",
            "with shared schedule confirmed, departure margin, and conservative remote-access timing",
        ),
        (
            "with departure transfer margin with transfer buffers for traffic-aware movement",
            "with departure and transfer buffers for traffic-aware movement",
        ),
    ]

    for old, new in replacements:
        compacted = compacted.replace(old, new)
    return compacted


def _strengthen_timing_step(step: str, destination_policy: dict[str, Any]) -> str:
    if not step.startswith("Confirm the trip timing"):
        return step

    suffix = _destination_pacing_suffix(destination_policy)
    if not suffix or suffix in step or (
        "heat-aware" in suffix and "heat-aware" in step
    ):
        return step
    compacted_suffixes = {
        "with transfer buffers for traffic-aware movement": "with departure and transfer buffers for traffic-aware movement",
        "with drive-time buffers for access conditions": "with departure and drive-time buffers for access conditions",
        "with conservative remote-access timing": "with departure margin and conservative remote-access timing",
    }
    compacted_suffix = compacted_suffixes.get(suffix)
    if compacted_suffix and compacted_suffix in step:
        return step
    return f"{step} {suffix}"


def _strengthen_accommodation_visibility(step: str, destination_policy: dict[str, Any]) -> str:
    if not step.startswith("Choose ") or "transport arrangements" not in step:
        return step

    accommodation_label = _accommodation_label(destination_policy)
    if not accommodation_label:
        return step
    clause = f"; lodging should account for {accommodation_label.removeprefix('including ')}"
    if clause in step:
        return step
    return f"{step}{clause}"


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


def _accommodation_label(destination_policy: dict[str, Any]) -> str:
    accommodation_bias = destination_policy.get("accommodation_bias")
    destination_type = destination_policy.get("destination_type")
    if accommodation_bias in {"resort_or_beachfront", "boutique_or_beachfront", "beachfront"}:
        return "including beachfront or resort-style stays"
    if accommodation_bias == "lodge_or_cabin":
        return "including lodges or cabins near access points"
    if accommodation_bias == "camp_or_lodge":
        return "including camp or lodge stays aligned with drive times"
    if accommodation_bias == "city_hotel":
        return "including city hotels near movement corridors"
    if destination_type == "arid" and accommodation_bias in {"basic_lodge", "camp"}:
        return "including stays that support remote access logistics"
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
    accommodation_label = _accommodation_label(constraints["destination_policy"])
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
    if step == transport_template or step.startswith(f"{transport_template};") or step.startswith(f"{transport_template} "):
        context = f"{destination_label} " if destination_label else ""
        budget = f" with {budget_label} choices" if budget_label else ""
        group = f" for {traveller_label} coordination" if traveller_label else ""
        lodging = f" {accommodation_label}" if accommodation_label else ""
        tail = step.removeprefix(transport_template)
        return f"Choose {context}transport and lodging options for {destination} that fit the trip{budget}{group}{lodging}{tail}"

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
            refined_step = _strengthen_accommodation_visibility(refined_step, constraints["destination_policy"])
            refined_step = _strengthen_timing_step(refined_step, constraints["destination_policy"])
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

    if not _has_operational_check_categories(checks):
        checks = _default_operational_checks()

    if len(risks) < 6:
        risks = _default_operational_risks()

    refined["checks"], refined["risks"] = _trip_refinement(checks, risks, constraints)
    changed_sections = ["checks", "risks"]
    if refined["steps"] != original_steps:
        changed_sections.insert(0, "steps")

    return PlanRefinementResult(
        refined_plan=refined,
        changed_sections=changed_sections,
    ).refined_plan
