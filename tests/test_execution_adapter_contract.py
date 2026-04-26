from contracts.execution_adapter_contract import ExecutionAdapterRequest
from engine.execution_adapter import run_execution_adapter_dry_run


def _request(**overrides) -> ExecutionAdapterRequest:
    data = {
        "trace_id": "trace-123",
        "adapter_name": "calendar_review",
        "adapter_version": "v1",
        "action_class": "review_only",
        "requested_action": "calendar_review",
        "dry_run": True,
        "idempotency_key": "trace-123:calendar_review:payload",
        "workflow_state": "plan_ready_only",
        "readiness_level": "plan_ready_only",
        "approval_state": "not_requested",
        "goal": "Plan a trip to Diani",
        "travel_brief": {
            "destination": "diani",
            "traveller_count": 2,
            "timing": {"state": "relative_timing", "raw_text": "next weekend"},
        },
        "blockers": [],
        "target_parameters": {"destination": "diani"},
        "resource_identifiers": {"calendar_id": "primary"},
        "payload": {"action": "review", "timing": "next weekend"},
        "mapping_schema_version": "adapter.schema.v1",
        "created_at": "2026-04-26T00:00:00Z",
    }
    data.update(overrides)
    return ExecutionAdapterRequest(**data)


def test_valid_review_only_dry_run_returns_normalized_result():
    result = run_execution_adapter_dry_run(_request())

    assert result.status == "success"
    assert result.dry_run is True
    assert result.action_class == "review_only"
    assert result.requested_action == "calendar_review"
    assert result.mutation_attempted is False
    assert result.mutation_performed is False
    assert result.failure_class is None
    assert result.payload_hash
    assert result.created_at == "2026-04-26T00:00:00Z"
    assert result.completed_at == "2026-04-26T00:00:00Z"


def test_missing_idempotency_key_hard_fails():
    result = run_execution_adapter_dry_run(_request(idempotency_key=None))

    assert result.status == "failure"
    assert result.failure_class == "precondition_failed"
    assert result.mutation_attempted is False
    assert result.recovery_guidance == "Provide a deterministic idempotency key."


def test_missing_required_payload_fields_fail_as_input_incomplete():
    result = run_execution_adapter_dry_run(_request(payload={}))

    assert result.status == "failure"
    assert result.failure_class == "input_incomplete"
    assert result.message == "Adapter request is missing explicit execution inputs."


def test_incompatible_workflow_precondition_fails():
    result = run_execution_adapter_dry_run(
        _request(workflow_state="execution_blocked")
    )

    assert result.status == "failure"
    assert result.failure_class == "precondition_failed"
    assert result.message == "workflow_state is not compatible with review_only adapter entry."


def test_dry_run_false_is_policy_blocked():
    result = run_execution_adapter_dry_run(_request(dry_run=False))

    assert result.status == "failure"
    assert result.failure_class == "policy_blocked"
    assert result.mutation_attempted is False
    assert result.mutation_performed is False


def test_prep_only_can_pass_when_plan_ready():
    result = run_execution_adapter_dry_run(
        _request(
            adapter_name="booking_prep",
            action_class="prep_only",
            requested_action="booking_prep",
            resource_identifiers={"handoff_target": "operator"},
            payload={"action": "prepare_booking_packet"},
        )
    )

    assert result.status == "success"
    assert result.action_class == "prep_only"
    assert result.mutation_attempted is False
    assert result.mutation_performed is False


def test_mutation_capable_preview_never_performs_live_mutation():
    result = run_execution_adapter_dry_run(
        _request(
            adapter_name="calendar_schedule",
            action_class="mutation_capable",
            requested_action="calendar_schedule",
            workflow_state="execution_prep_ready",
            readiness_level="execution_ready",
            approval_state="approved",
            resource_identifiers={"calendar_id": "primary"},
            payload={"action": "schedule_preview", "start": "2026-04-27"},
        )
    )

    assert result.status == "success"
    assert result.action_class == "mutation_capable"
    assert result.mutation_attempted is False
    assert result.mutation_performed is False


def test_mutation_capable_preview_requires_approval():
    result = run_execution_adapter_dry_run(
        _request(
            action_class="mutation_capable",
            requested_action="calendar_schedule",
            workflow_state="execution_prep_ready",
            readiness_level="execution_ready",
            approval_state="pending",
        )
    )

    assert result.status == "failure"
    assert result.failure_class == "approval_missing"


def test_repeated_dry_run_is_deterministic_for_identical_request():
    request = _request()

    first = run_execution_adapter_dry_run(request)
    second = run_execution_adapter_dry_run(request)

    assert first.model_dump() == second.model_dump()
