from __future__ import annotations

from typing import Any

from contracts.execution_readiness_contract import (
    ExecutionReadinessRequest,
    ExecutionReadinessResult,
)


PLAN_READY_TIMING_STATES = {
    "exact_timing",
    "relative_timing",
    "duration_only",
    "month_only",
}
EXECUTION_READY_TIMING_STATES = {"exact_timing"}
ALL_ACTIONS = [
    "plan_display",
    "calendar_review",
    "calendar_schedule",
    "booking_prep",
]


def evaluate_execution_readiness(
    request: ExecutionReadinessRequest,
) -> ExecutionReadinessResult:
    brief = request.brief
    timing = _timing_from(brief, request.planning_constraints)
    timing_state = timing.get("state") or timing.get("timing_state") or "missing_timing"

    blocking_reasons = _blocking_reasons(
        brief=brief,
        timing=timing,
        timing_state=timing_state,
        plan_status=request.plan_status,
    )
    plan_ready = _is_plan_ready(brief, timing_state, request.plan_status)
    execution_ready = plan_ready and not blocking_reasons
    readiness_level = _readiness_level(plan_ready, execution_ready)
    allowed_actions = _allowed_actions(plan_ready, execution_ready)
    blocked_actions = [action for action in ALL_ACTIONS if action not in allowed_actions]

    if request.requested_action and request.requested_action not in allowed_actions:
        blocked_actions = _dedupe(blocked_actions + [request.requested_action])

    return ExecutionReadinessResult(
        plan_ready=plan_ready,
        execution_ready=execution_ready,
        execution_blocked=not execution_ready,
        readiness_level=readiness_level,
        blocking_reasons=blocking_reasons,
        allowed_actions=allowed_actions,
        blocked_actions=blocked_actions,
    )


def _timing_from(brief: dict[str, Any], planning_constraints: dict[str, Any] | None) -> dict[str, Any]:
    timing = brief.get("timing") or {}
    if timing:
        return timing
    if not planning_constraints:
        return {}
    return planning_constraints.get("timing_policy") or {}


def _is_plan_ready(brief: dict[str, Any], timing_state: str, plan_status: str | None) -> bool:
    if plan_status is not None and plan_status != "pass":
        return False
    return bool(
        brief.get("destination")
        and brief.get("traveller_count") is not None
        and timing_state in PLAN_READY_TIMING_STATES
    )


def _blocking_reasons(
    brief: dict[str, Any],
    timing: dict[str, Any],
    timing_state: str,
    plan_status: str | None,
) -> list[str]:
    reasons: list[str] = []

    if plan_status is not None and plan_status != "pass":
        reasons.append("plan_status_not_pass")
    if not brief.get("destination"):
        reasons.append("missing_destination")
    if brief.get("traveller_count") is None:
        reasons.append("missing_traveller_count")
    if timing_state not in EXECUTION_READY_TIMING_STATES:
        reasons.append(f"execution_timing_not_exact:{timing_state}")
    elif not timing.get("start_date") or not timing.get("end_date"):
        reasons.append("execution_timing_missing_date_range")

    return reasons


def _readiness_level(plan_ready: bool, execution_ready: bool) -> str:
    if execution_ready:
        return "execution_ready"
    if plan_ready:
        return "plan_ready_only"
    return "not_plan_ready"


def _allowed_actions(plan_ready: bool, execution_ready: bool) -> list[str]:
    if execution_ready:
        return list(ALL_ACTIONS)
    if plan_ready:
        return ["plan_display", "calendar_review"]
    return []


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
