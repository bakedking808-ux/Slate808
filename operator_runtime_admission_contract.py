from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from operator_state_contract import OperatorStateAction


class OperatorRuntimeAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    operator_action: OperatorStateAction
    operator_class: str
    readiness: str


class OperatorRuntimeAdmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    allowed: bool
    reason: str
    operator_class: str
    readiness: str
    action: str


def admit_operator_runtime(
    request: OperatorRuntimeAdmissionRequest,
) -> OperatorRuntimeAdmissionResult:
    if request.readiness not in _READINESS_STATES:
        raise ValueError("request.readiness must be one of: not_ready, ready")

    if request.operator_class not in _OPERATOR_CLASSES:
        raise ValueError(
            "request.operator_class must be one of: execution_triggering, state_shaping"
        )

    allowed = (
        request.operator_class == "state_shaping"
        or request.readiness == "ready"
    )
    reason = _allowed_reason(request) if allowed else _blocked_reason()

    return OperatorRuntimeAdmissionResult(
        allowed=allowed,
        reason=reason,
        operator_class=request.operator_class,
        readiness=request.readiness,
        action=request.operator_action.action,
    )


def _allowed_reason(request: OperatorRuntimeAdmissionRequest) -> str:
    if request.operator_class == "state_shaping":
        return "State-shaping operator action admitted."

    return "Execution-triggering operator action admitted after readiness."


def _blocked_reason() -> str:
    return "Execution-triggering operator action blocked until readiness is ready."


_OPERATOR_CLASSES = {"execution_triggering", "state_shaping"}
_READINESS_STATES = {"not_ready", "ready"}
