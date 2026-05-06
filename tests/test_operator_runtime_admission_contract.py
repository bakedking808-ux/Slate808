import pytest
from pydantic import ValidationError

from contracts.operator_runtime_admission_contract import (
    OperatorRuntimeAdmissionRequest,
    admit_operator_runtime,
)
from contracts.operator_state_contract import OperatorStateAction


def _action(action: str = "replace_field") -> OperatorStateAction:
    return OperatorStateAction(
        action=action,
        target_field="traveller_count",
        reset_required=False,
        resume_allowed=True,
        reason="test action",
    )


def _execution_request(**overrides) -> OperatorRuntimeAdmissionRequest:
    data = {
        "operator_action": _action("complete_flow"),
        "operator_class": "execution_triggering",
        "readiness": "ready",
        "requested_action": "booking_prep",
        "action_allowed": True,
        "workflow_state": "execution_prep_ready",
        "approval_state": "approved",
        "requires_human_approval": True,
        "blocked_actions": [],
        "blockers": [],
    }
    data.update(overrides)
    return OperatorRuntimeAdmissionRequest(**data)


def test_state_shaping_operator_allowed_before_readiness():
    result = admit_operator_runtime(
        OperatorRuntimeAdmissionRequest(
            operator_action=_action(),
            operator_class="state_shaping",
            readiness="not_ready",
        )
    )

    assert result.allowed is True
    assert result.reason == "State-shaping operator action admitted."


def test_execution_triggering_operator_blocked_before_readiness():
    result = admit_operator_runtime(_execution_request(readiness="not_ready"))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: readiness_not_ready."


def test_execution_triggering_operator_allowed_after_readiness():
    result = admit_operator_runtime(_execution_request())

    assert result.allowed is True
    assert result.reason == "Execution-triggering operator action admitted after full authorization gate."


def test_execution_triggering_rejects_missing_requested_action():
    result = admit_operator_runtime(_execution_request(requested_action=None))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: missing_requested_action."


def test_execution_triggering_rejects_action_allowed_none():
    result = admit_operator_runtime(_execution_request(action_allowed=None))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: action_not_allowed."


def test_execution_triggering_rejects_action_allowed_false():
    result = admit_operator_runtime(_execution_request(action_allowed=False))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: action_not_allowed."


def test_execution_triggering_rejects_when_approval_required_but_pending():
    result = admit_operator_runtime(_execution_request(approval_state="pending"))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: approval_required."


def test_execution_triggering_rejects_incompatible_workflow():
    result = admit_operator_runtime(_execution_request(workflow_state="plan_ready_only"))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: workflow_not_execution_compatible."


def test_execution_triggering_rejects_blocked_requested_action():
    result = admit_operator_runtime(
        _execution_request(blocked_actions=["booking_prep"])
    )

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: requested_action_blocked."


def test_execution_triggering_admits_full_valid_gate():
    result = admit_operator_runtime(_execution_request())

    assert result.allowed is True


def test_execution_triggering_rejects_unresolved_blockers():
    result = admit_operator_runtime(_execution_request(blockers=["missing_destination"]))

    assert result.allowed is False
    assert result.reason == "Execution-triggering operator action blocked: unresolved_blockers."


def test_unknown_operator_class_rejected_loudly():
    request = OperatorRuntimeAdmissionRequest(
        operator_action=_action(),
        operator_class="unknown",
        readiness="ready",
    )

    with pytest.raises(
        ValueError,
        match="request.operator_class must be one of: execution_triggering, state_shaping",
    ):
        admit_operator_runtime(request)


def test_invalid_readiness_rejected_loudly():
    request = OperatorRuntimeAdmissionRequest(
        operator_action=_action(),
        operator_class="state_shaping",
        readiness="almost_ready",
    )

    with pytest.raises(
        ValueError,
        match="request.readiness must be one of: not_ready, ready, execution_ready",
    ):
        admit_operator_runtime(request)


def test_malformed_admission_request_rejected_loudly():
    with pytest.raises(ValidationError):
        OperatorRuntimeAdmissionRequest(
            operator_action=_action(),
            readiness="ready",
        )


def test_repeated_call_determinism_for_identical_admission_inputs():
    request = OperatorRuntimeAdmissionRequest(
        operator_action=_action(),
        operator_class="state_shaping",
        readiness="not_ready",
    )

    first = admit_operator_runtime(request)
    second = admit_operator_runtime(request)

    assert first.model_dump() == second.model_dump()
