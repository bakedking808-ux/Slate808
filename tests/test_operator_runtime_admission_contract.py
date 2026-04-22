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
    result = admit_operator_runtime(
        OperatorRuntimeAdmissionRequest(
            operator_action=_action("complete_flow"),
            operator_class="execution_triggering",
            readiness="not_ready",
        )
    )

    assert result.allowed is False
    assert (
        result.reason
        == "Execution-triggering operator action blocked until readiness is ready."
    )


def test_execution_triggering_operator_allowed_after_readiness():
    result = admit_operator_runtime(
        OperatorRuntimeAdmissionRequest(
            operator_action=_action("complete_flow"),
            operator_class="execution_triggering",
            readiness="ready",
        )
    )

    assert result.allowed is True
    assert result.reason == "Execution-triggering operator action admitted after readiness."


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
        match="request.readiness must be one of: not_ready, ready",
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
