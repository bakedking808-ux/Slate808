from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from contracts.itinerary_builder_contract import ItineraryPlan, build_itinerary_plan
from contracts.itinerary_input_contract import ItineraryRequest
from contracts.operator_runtime_admission_contract import (
    OperatorRuntimeAdmissionRequest,
    OperatorRuntimeAdmissionResult,
    admit_operator_runtime,
)


class OperatorRuntimeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["blocked", "success", "failure"]
    transition: Literal[
        "blocked",
        "rejected_by_action_guard",
        "failed",
        "succeeded",
    ]
    admission: OperatorRuntimeAdmissionResult
    state: dict[str, Any] | None = None
    result: ItineraryPlan | None = None
    error: str | None = None


def execute_admitted_itinerary_operator(
    admission_request: OperatorRuntimeAdmissionRequest,
    itinerary_request: ItineraryRequest,
    downstream_operator: Callable[[ItineraryRequest], ItineraryPlan] = build_itinerary_plan,
) -> OperatorRuntimeExecutionResult:
    admission = admit_operator_runtime(admission_request)
    if admission.allowed is not True:
        return OperatorRuntimeExecutionResult(
            status="blocked",
            transition="blocked",
            admission=admission,
        )

    if admission.action != "complete_flow":
        return OperatorRuntimeExecutionResult(
            status="failure",
            transition="rejected_by_action_guard",
            admission=admission,
            error="Unsupported execution-triggering operator action.",
        )

    try:
        result = downstream_operator(itinerary_request)
    except Exception as exc:
        return OperatorRuntimeExecutionResult(
            status="failure",
            transition="failed",
            admission=admission,
            error=f"Downstream operator invocation failed: {exc}",
        )

    if not isinstance(result, ItineraryPlan):
        return OperatorRuntimeExecutionResult(
            status="failure",
            transition="failed",
            admission=admission,
            error="Downstream operator returned invalid result.",
        )

    return OperatorRuntimeExecutionResult(
        status="success",
        transition="succeeded",
        admission=admission,
        result=result,
    )
