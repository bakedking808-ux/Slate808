from clarification_state import ClarificationStateManager
import operator_runtime_execution_contract
from operator_runtime_admission_contract import OperatorRuntimeAdmissionRequest
from operator_runtime_state_shaping_contract import apply_admitted_supply_field_operator
from operator_state_contract import OperatorStateAction


_RESULT_KEYS = ["status", "transition", "admission", "state", "result", "error"]


def _manager() -> ClarificationStateManager:
    manager = ClarificationStateManager()
    manager.start(
        task_type="trip",
        original_input="Plan a trip to mara",
        missing_fields=["traveller_count", "timing"],
        collected_fields={"destination": "mara"},
        trace_id="test-trace",
    )
    return manager


def _action(action: str = "supply_field") -> OperatorStateAction:
    return OperatorStateAction(
        action=action,
        target_field="traveller_count",
        reset_required=False,
        resume_allowed=True,
        reason="test action",
    )


def _admission_request(
    operator_class: str = "state_shaping",
    readiness: str = "not_ready",
    action: str = "supply_field",
) -> OperatorRuntimeAdmissionRequest:
    return OperatorRuntimeAdmissionRequest(
        operator_action=_action(action),
        operator_class=operator_class,
        readiness=readiness,
    )


def test_admitted_supply_field_state_shaping_allowed_before_readiness():
    result = apply_admitted_supply_field_operator(
        _admission_request(),
        _manager(),
        2,
    )

    assert result.status == "success"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "succeeded"
    assert result.state is not None
    assert result.result is None
    assert result.error is None
    assert result.state["collected_fields"]["traveller_count"] == 2


def test_state_shaping_updates_only_intended_state_element():
    result = apply_admitted_supply_field_operator(
        _admission_request(),
        _manager(),
        2,
    )

    assert result.state is not None
    assert result.state["collected_fields"] == {
        "destination": "mara",
        "traveller_count": 2,
    }
    assert result.state["missing_fields"] == ["timing"]
    assert result.state["current_field"] == "timing"


def test_state_shaping_path_does_not_invoke_downstream_execution(monkeypatch):
    invoked = False

    def downstream_execution(_):
        nonlocal invoked
        invoked = True

    monkeypatch.setattr(
        operator_runtime_execution_contract,
        "build_itinerary_plan",
        downstream_execution,
    )

    result = apply_admitted_supply_field_operator(
        _admission_request(),
        _manager(),
        2,
    )

    assert result.status == "success"
    assert invoked is False


def test_unsupported_state_shaping_action_is_rejected_loudly():
    manager = _manager()

    result = apply_admitted_supply_field_operator(
        _admission_request(action="replace_field"),
        manager,
        2,
    )

    assert result.status == "failure"
    assert result.transition == "rejected_by_action_guard"
    assert result.state is None
    assert result.result is None
    assert result.error == "Unsupported state-shaping operator action."
    assert manager.get_state()["collected_fields"] == {"destination": "mara"}


def test_invalid_state_update_input_returns_structured_failure(monkeypatch):
    invoked = False
    manager = _manager()
    action = OperatorStateAction(
        action="supply_field",
        target_field="timing",
        reset_required=False,
        resume_allowed=True,
        reason="test action",
    )

    def downstream_execution(_):
        nonlocal invoked
        invoked = True

    monkeypatch.setattr(
        operator_runtime_execution_contract,
        "build_itinerary_plan",
        downstream_execution,
    )

    result = apply_admitted_supply_field_operator(
        OperatorRuntimeAdmissionRequest(
            operator_action=action,
            operator_class="state_shaping",
            readiness="not_ready",
        ),
        manager,
        "next month",
    )

    assert result.status == "failure"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "failed"
    assert result.state is None
    assert result.result is None
    assert (
        result.error
        == "State-shaping update failed: Field mismatch. Expected 'traveller_count', got 'timing'."
    )
    assert invoked is False
    assert manager.get_state()["collected_fields"] == {"destination": "mara"}


def test_repeated_call_determinism_for_identical_inputs():
    first = apply_admitted_supply_field_operator(
        _admission_request(),
        _manager(),
        2,
    )
    second = apply_admitted_supply_field_operator(
        _admission_request(),
        _manager(),
        2,
    )

    assert first.model_dump() == second.model_dump()


def test_execution_triggering_before_readiness_remains_blocked():
    manager = _manager()

    result = apply_admitted_supply_field_operator(
        _admission_request(
            operator_class="execution_triggering",
            readiness="not_ready",
            action="complete_flow",
        ),
        manager,
        2,
    )

    assert result.status == "blocked"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "blocked"
    assert result.admission.allowed is False
    assert result.state is None
    assert result.result is None
    assert result.error is None
    assert manager.get_state()["collected_fields"] == {"destination": "mara"}
