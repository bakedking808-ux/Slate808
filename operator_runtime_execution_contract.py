from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from itinerary_builder_contract import ItineraryPlan, build_itinerary_plan
from itinerary_input_contract import ItineraryRequest
from operator_runtime_admission_contract import (
    OperatorRuntimeAdmissionRequest,
    OperatorRuntimeAdmissionResult,
    admit_operator_runtime,
)


class OperatorRuntimeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["blocked", "success", "failure"]
    admission: OperatorRuntimeAdmissionResult
    result: ItineraryPlan | None = None
    error: str | None = None


def execute_admitted_itinerary_operator(
    admission_request: OperatorRuntimeAdmissionRequest,
    itinerary_request: ItineraryRequest,
    downstream_operator: Callable[[ItineraryRequest], ItineraryPlan] = build_itinerary_plan,
) -> OperatorRuntimeExecutionResult:
    admission = admit_operator_runtime(admission_request)
    if admission.allowed is not True:
        return OperatorRuntimeExecutionResult(status="blocked", admission=admission)

    try:
        result = downstream_operator(itinerary_request)
    except Exception as exc:
        return OperatorRuntimeExecutionResult(
            status="failure",
            admission=admission,
            error=f"Downstream operator invocation failed: {exc}",
        )

    if not isinstance(result, ItineraryPlan):
        return OperatorRuntimeExecutionResult(
            status="failure",
            admission=admission,
            error="Downstream operator returned invalid result.",
        )

    return OperatorRuntimeExecutionResult(
        status="success",
        admission=admission,
        result=result,
    )
