from contracts.execution_readiness_contract import ExecutionReadinessRequest
from contracts.operator_flow_contract import classify_operator_flow
from contracts.operator_state_contract import interpret_operator_state
from contracts.operator_workflow_contract import (
    OperatorWorkflowInput,
    map_operator_workflow,
)
from engine.execution_readiness import evaluate_execution_readiness
from engine.planning_policy import build_planning_constraints
from engine.runner import run_engine
from engine.travel_brief import build_travel_brief


def _readiness(text: str, requested_action: str | None = None) -> dict:
    brief = build_travel_brief(text)
    return evaluate_execution_readiness(
        ExecutionReadinessRequest(
            brief=brief,
            planning_constraints=build_planning_constraints(brief),
            plan_status="pass",
            requested_action=requested_action,
        )
    ).model_dump()


def test_missing_destination_routes_to_clarification_required():
    result = map_operator_workflow(
        OperatorWorkflowInput(
            status="pass",
            clarification_needed=True,
            missing_fields=["destination"],
        )
    )

    assert result.state == "clarification_required"
    assert result.transition == "clarification_required"
    assert result.recovery_action == "request_missing_fields"
    assert "supply_field" in result.allowed_operator_actions


def test_active_clarification_routes_to_in_progress_state():
    result = map_operator_workflow(
        OperatorWorkflowInput(
            clarification_active=True,
            missing_fields=["timing"],
        )
    )

    assert result.state == "clarification_in_progress"
    assert result.recovery_action == "supply_requested_field"


def test_relative_timing_routes_to_plan_ready_only_without_execution_action():
    readiness = _readiness("Plan a trip to Diani for 2 people next weekend")

    result = map_operator_workflow(
        OperatorWorkflowInput(status="pass", execution_readiness=readiness)
    )

    assert result.state == "plan_ready_only"
    assert result.execution_prep_eligible is False
    assert "calendar_review" in result.allowed_operator_actions
    assert "booking_prep" in result.blocked_operator_actions


def test_booking_request_with_relative_timing_stays_execution_blocked():
    readiness = _readiness(
        "Plan a trip to Diani for 2 people next weekend",
        requested_action="booking_prep",
    )

    result = map_operator_workflow(
        OperatorWorkflowInput(status="pass", execution_readiness=readiness)
    )

    assert result.state == "execution_blocked"
    assert result.transition == "execution_blocked"
    assert result.recovery_action == "resolve_execution_blockers"
    assert "booking_prep" in result.blocked_operator_actions


def test_calendar_review_is_softer_than_calendar_schedule_for_plan_ready_only():
    review = map_operator_workflow(
        OperatorWorkflowInput(
            status="pass",
            execution_readiness=_readiness(
                "Plan a trip to Diani for 2 people next weekend",
                requested_action="calendar_review",
            ),
        )
    )
    schedule = map_operator_workflow(
        OperatorWorkflowInput(
            status="pass",
            execution_readiness=_readiness(
                "Plan a trip to Diani for 2 people next weekend",
                requested_action="calendar_schedule",
            ),
        )
    )

    assert review.state == "plan_ready_only"
    assert "calendar_review" in review.allowed_operator_actions
    assert schedule.state == "execution_blocked"
    assert "calendar_schedule" in schedule.blocked_operator_actions


def test_exact_date_range_requires_human_approval_before_execution_prep():
    readiness = _readiness("Plan a trip to Diani for 2 people 10 April to 12 April")

    result = map_operator_workflow(
        OperatorWorkflowInput(status="pass", execution_readiness=readiness)
    )

    assert result.state == "human_approval_required"
    assert result.requires_human_approval is True
    assert result.execution_prep_eligible is False
    assert "booking_prep" in result.blocked_operator_actions


def test_approved_exact_date_range_becomes_execution_prep_ready():
    readiness = _readiness("Plan a trip to Diani for 2 people 10 April to 12 April")

    result = map_operator_workflow(
        OperatorWorkflowInput(
            status="pass",
            execution_readiness=readiness,
            approval_state="approved",
        )
    )

    assert result.state == "execution_prep_ready"
    assert result.execution_prep_eligible is True
    assert result.requires_human_approval is False


def test_handoff_packet_uses_existing_trace_brief_readiness_and_approval():
    text = "Plan a trip to Diani for 2 people 10 April to 12 April"
    brief = build_travel_brief(text)
    readiness = _readiness(text)

    result = map_operator_workflow(
        OperatorWorkflowInput(
            status="pass",
            trace_id="trace-123",
            brief=brief,
            execution_readiness=readiness,
            approval_state="approved",
            create_handoff_packet=True,
        )
    )

    assert result.state == "handoff_packet_created"
    assert result.handoff_packet is not None
    assert result.handoff_packet.trace_id == "trace-123"
    assert result.handoff_packet.brief == brief
    assert result.handoff_packet.readiness == readiness
    assert result.handoff_packet.approval_state == "approved"


def test_goal_shift_or_reset_maps_to_scope_reset():
    operator_state = interpret_operator_state(
        classify_operator_flow("Let's switch to a beach trip instead.")
    )
    assert operator_state.action is not None

    result = map_operator_workflow(
        OperatorWorkflowInput(operator_action=operator_state.action)
    )

    assert result.state == "scope_reset"
    assert result.transition == "scope_reset"
    assert "operator_scope_reset" in result.audit_tags


def test_workflow_mapping_is_deterministic_and_auditable():
    readiness = _readiness(
        "Plan a trip to Diani for 2 people next weekend",
        requested_action="booking_prep",
    )
    request = OperatorWorkflowInput(status="pass", execution_readiness=readiness)

    first = map_operator_workflow(request)
    second = map_operator_workflow(request)

    assert first.model_dump() == second.model_dump()
    assert first.audit_tags == ["execution_blocked", "plan_ready_only"]


def test_action_blocked_status_still_maps_to_execution_blocked():
    readiness = _readiness(
        "Plan a trip to Diani for 2 people next weekend",
        requested_action="booking_prep",
    )

    result = map_operator_workflow(
        OperatorWorkflowInput(status="fail", execution_readiness=readiness)
    )

    assert result.state == "execution_blocked"
    assert result.recovery_action == "resolve_execution_blockers"


def test_runtime_logs_operator_workflow_for_plan_ready_only(monkeypatch):
    entries = []
    monkeypatch.setattr("engine.runner.log_run", lambda entry: entries.append(entry))
    monkeypatch.setattr("engine.runner.log_event", lambda **_: None)

    run_engine("Plan a trip to diani for 2 people next weekend")

    workflow = entries[-1]["final_output"]["operator_workflow"]
    assert workflow["state"] == "plan_ready_only"
    assert workflow["execution_prep_eligible"] is False
    assert workflow["audit_tags"] == ["plan_ready_only"]


def test_runtime_logs_human_approval_required_for_exact_timing(monkeypatch):
    entries = []
    monkeypatch.setattr("engine.runner.log_run", lambda entry: entries.append(entry))
    monkeypatch.setattr("engine.runner.log_event", lambda **_: None)

    run_engine("Plan a trip to diani for 2 people 10 April to 12 April")

    workflow = entries[-1]["final_output"]["operator_workflow"]
    assert workflow["state"] == "human_approval_required"
    assert workflow["requires_human_approval"] is True
    assert workflow["execution_prep_eligible"] is False


def test_runtime_logs_execution_blocked_for_booking_with_relative_timing(monkeypatch):
    entries = []
    monkeypatch.setattr("engine.runner.log_run", lambda entry: entries.append(entry))
    monkeypatch.setattr("engine.runner.log_event", lambda **_: None)

    run_engine("Plan a trip to diani for 2 people next weekend and book it")

    final_output = entries[-1]["final_output"]
    workflow = final_output["operator_workflow"]
    assert final_output["status"] == "fail"
    assert workflow["state"] == "execution_blocked"
    assert workflow["recovery_action"] == "resolve_execution_blockers"
