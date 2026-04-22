from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from clarification_state import ClarificationStateManager
from contracts.operator_runtime_admission_contract import (
    OperatorRuntimeAdmissionRequest,
    OperatorRuntimeAdmissionResult,
    admit_operator_runtime,
)


OperatorRuntimeStateTransition = Literal[
    "blocked",
    "rejected_by_action_guard",
    "failed",
    "succeeded",
]


class OperatorRuntimeStateShapeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["blocked", "success", "failure"]
    transition: OperatorRuntimeStateTransition
    admission: OperatorRuntimeAdmissionResult
    state: dict[str, Any] | None = None
    result: None = None
    error: str | None = None


def apply_admitted_supply_field_operator(
    admission_request: OperatorRuntimeAdmissionRequest,
    state_manager: ClarificationStateManager,
    value: Any,
) -> OperatorRuntimeStateShapeResult:
    admission = admit_operator_runtime(admission_request)
    if admission.allowed is not True:
        return OperatorRuntimeStateShapeResult(
            status="blocked",
            transition="blocked",
            admission=admission,
        )

    if admission.operator_class != "state_shaping" or admission.action != "supply_field":
        return OperatorRuntimeStateShapeResult(
            status="failure",
            transition="rejected_by_action_guard",
            admission=admission,
            error="Unsupported state-shaping operator action.",
        )

    target_field = admission_request.operator_action.target_field
    if target_field is None:
        return OperatorRuntimeStateShapeResult(
            status="failure",
            transition="failed",
            admission=admission,
            error="State-shaping supply_field action requires target_field.",
        )

    try:
        state = state_manager.update_with_field(target_field, value)
    except Exception as exc:
        return OperatorRuntimeStateShapeResult(
            status="failure",
            transition="failed",
            admission=admission,
            error=f"State-shaping update failed: {exc}",
        )

    return OperatorRuntimeStateShapeResult(
        status="success",
        transition="succeeded",
        admission=admission,
        state=state,
    )
