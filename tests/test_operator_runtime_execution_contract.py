from itinerary_builder_contract import ItineraryPlan, build_itinerary_plan
from itinerary_input_contract import ItineraryRequest
from operator_runtime_admission_contract import OperatorRuntimeAdmissionRequest
from operator_runtime_execution_contract import execute_admitted_itinerary_operator
from operator_state_contract import OperatorStateAction


_RESULT_KEYS = ["status", "transition", "admission", "state", "result", "error"]


def _operator_action() -> OperatorStateAction:
    return OperatorStateAction(
        action="complete_flow",
        target_field=None,
        reset_required=False,
        resume_allowed=False,
        reason="Operator input signals acceptance or completion.",
    )


def _admission_request(readiness: str) -> OperatorRuntimeAdmissionRequest:
    return OperatorRuntimeAdmissionRequest(
        operator_action=_operator_action(),
        operator_class="execution_triggering",
        readiness=readiness,
    )


def _itinerary_request() -> ItineraryRequest:
    return ItineraryRequest(
        destination="destination_fixed",
        traveller="family",
        timing="weekend_trip",
        budget=None,
        intent=None,
        activity=None,
        transport=None,
        accommodation=None,
        constraints=None,
        calendar=None,
        ready=True,
    )


def test_blocked_admission_prevents_operator_invocation():
    calls: list[ItineraryRequest] = []

    def downstream(request: ItineraryRequest) -> ItineraryPlan:
        calls.append(request)
        return build_itinerary_plan(request)

    result = execute_admitted_itinerary_operator(
        _admission_request("not_ready"),
        _itinerary_request(),
        downstream,
    )

    assert result.status == "blocked"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "blocked"
    assert result.admission.allowed is False
    assert result.state is None
    assert result.result is None
    assert result.error is None
    assert calls == []


def test_admitted_path_invokes_downstream_operator_exactly_once():
    calls: list[ItineraryRequest] = []

    def downstream(request: ItineraryRequest) -> ItineraryPlan:
        calls.append(request)
        return build_itinerary_plan(request)

    result = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
        downstream,
    )

    assert result.status == "success"
    assert len(calls) == 1


def test_admitted_non_complete_flow_action_does_not_invoke_downstream():
    calls: list[ItineraryRequest] = []
    action = OperatorStateAction(
        action="shift_goal",
        target_field=None,
        reset_required=True,
        resume_allowed=False,
        reason="test action",
    )

    def downstream(request: ItineraryRequest) -> ItineraryPlan:
        calls.append(request)
        return build_itinerary_plan(request)

    result = execute_admitted_itinerary_operator(
        OperatorRuntimeAdmissionRequest(
            operator_action=action,
            operator_class="execution_triggering",
            readiness="ready",
        ),
        _itinerary_request(),
        downstream,
    )

    assert result.status == "failure"
    assert result.transition == "rejected_by_action_guard"
    assert result.state is None
    assert result.result is None
    assert result.error == "Unsupported execution-triggering operator action."
    assert calls == []


def test_admitted_path_returns_structured_success_result():
    result = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
    )

    assert result.status == "success"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "succeeded"
    assert result.state is None
    assert result.error is None
    assert result.result is not None
    assert result.result.title == "Trip Plan: destination_fixed"


def test_downstream_operator_failure_returns_structured_failure():
    def downstream(_: ItineraryRequest) -> ItineraryPlan:
        raise RuntimeError("operator failed")

    result = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
        downstream,
    )

    assert result.status == "failure"
    assert list(result.model_dump().keys()) == _RESULT_KEYS
    assert result.transition == "failed"
    assert result.state is None
    assert result.result is None
    assert result.error == "Downstream operator invocation failed: operator failed"


def test_downstream_invalid_result_returns_structured_failure():
    def downstream(_: ItineraryRequest):
        return {"invalid": True}

    result = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
        downstream,
    )

    assert result.status == "failure"
    assert result.transition == "failed"
    assert result.state is None
    assert result.result is None
    assert result.error == "Downstream operator returned invalid result."


def test_repeated_call_determinism_for_identical_inputs():
    first = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
    )
    second = execute_admitted_itinerary_operator(
        _admission_request("ready"),
        _itinerary_request(),
    )

    assert first.model_dump() == second.model_dump()
