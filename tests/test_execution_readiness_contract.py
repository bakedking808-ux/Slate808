from contracts.execution_readiness_contract import ExecutionReadinessRequest
from engine.execution_readiness import evaluate_execution_readiness
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "timing": build_timing(
            raw_text="10 april to 12 april",
            start_date="10 april",
            end_date="12 april",
            date_flexibility="fixed",
            state="exact_timing",
            confidence="high",
        ),
        "budget_amount": None,
        "budget_level": "unspecified",
        "trip_mood": None,
    }
    brief.update(overrides)
    return brief


def _result(brief, requested_action=None, plan_status="pass"):
    return evaluate_execution_readiness(
        ExecutionReadinessRequest(
            brief=brief,
            plan_status=plan_status,
            requested_action=requested_action,
        )
    )


def test_exact_timing_can_become_execution_ready():
    readiness = _result(_brief(), requested_action="calendar_schedule")

    assert readiness.plan_ready is True
    assert readiness.execution_ready is True
    assert readiness.execution_blocked is False
    assert readiness.readiness_level == "execution_ready"
    assert readiness.requested_action == "calendar_schedule"
    assert readiness.action_allowed is True
    assert "calendar_schedule" in readiness.allowed_actions
    assert readiness.blocking_reasons == []


def test_relative_timing_is_plan_ready_but_not_execution_ready():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            )
        ),
        requested_action="calendar_schedule",
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert readiness.readiness_level == "plan_ready_only"
    assert "calendar_review" in readiness.allowed_actions
    assert "calendar_schedule" in readiness.blocked_actions
    assert readiness.blocking_reasons == ["execution_timing_not_exact:relative_timing"]


def test_month_only_timing_is_blocked_for_execution():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="april",
                date_flexibility="flexible",
                state="month_only",
                confidence="low",
            )
        )
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert readiness.blocking_reasons == ["execution_timing_not_exact:month_only"]


def test_duration_only_timing_is_blocked_for_execution():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="for 3 days",
                duration_days=3,
                date_flexibility="unknown",
                state="duration_only",
                confidence="medium",
            )
        )
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert readiness.blocking_reasons == ["execution_timing_not_exact:duration_only"]


def test_missing_destination_blocks_execution():
    readiness = _result(_brief(destination=None))

    assert readiness.plan_ready is False
    assert readiness.execution_ready is False
    assert readiness.readiness_level == "not_plan_ready"
    assert "missing_destination" in readiness.blocking_reasons


def test_missing_traveller_count_blocks_execution():
    readiness = _result(_brief(traveller_count=None))

    assert readiness.plan_ready is False
    assert readiness.execution_ready is False
    assert readiness.readiness_level == "not_plan_ready"
    assert "missing_traveller_count" in readiness.blocking_reasons


def test_readiness_is_deterministic_across_repeated_calls():
    request = ExecutionReadinessRequest(
        brief=_brief(),
        plan_status="pass",
        requested_action="booking_prep",
    )

    first = evaluate_execution_readiness(request)
    second = evaluate_execution_readiness(request)

    assert first.model_dump() == second.model_dump()


def test_calendar_review_readiness_is_distinct_from_calendar_execution_readiness():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            )
        ),
        requested_action="calendar_review",
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert "calendar_review" in readiness.allowed_actions
    assert readiness.requested_action == "calendar_review"
    assert readiness.action_allowed is True
    assert "calendar_schedule" in readiness.blocked_actions


def test_calendar_schedule_action_is_blocked_without_execution_ready_timing():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            )
        ),
        requested_action="calendar_schedule",
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert readiness.requested_action == "calendar_schedule"
    assert readiness.action_allowed is False
    assert "calendar_schedule" in readiness.blocked_actions
    assert readiness.blocking_reasons == ["execution_timing_not_exact:relative_timing"]


def test_booking_prep_action_is_blocked_without_execution_ready_timing():
    readiness = _result(
        _brief(
            timing=build_timing(
                raw_text="for 3 days",
                duration_days=3,
                date_flexibility="unknown",
                state="duration_only",
                confidence="medium",
            )
        ),
        requested_action="booking_prep",
    )

    assert readiness.plan_ready is True
    assert readiness.execution_ready is False
    assert readiness.requested_action == "booking_prep"
    assert readiness.action_allowed is False
    assert "booking_prep" in readiness.blocked_actions
