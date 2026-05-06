from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contracts.operator_state_contract import OperatorStateAction


class OperatorRuntimeAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    operator_action: OperatorStateAction
    operator_class: str
    readiness: str
    requested_action: str | None = None
    action_allowed: bool | None = None
    workflow_state: str | None = None
    approval_state: str | None = None
    requires_human_approval: bool = False
    blocked_actions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


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
        raise ValueError("request.readiness must be one of: not_ready, ready, execution_ready")

    if request.operator_class not in _OPERATOR_CLASSES:
        raise ValueError(
            "request.operator_class must be one of: execution_triggering, state_shaping"
        )

    allowed, reason = _admission_decision(request)

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

    return "Execution-triggering operator action admitted after full authorization gate."


def _admission_decision(
    request: OperatorRuntimeAdmissionRequest,
) -> tuple[bool, str]:
    if request.operator_class == "state_shaping":
        return (True, _allowed_reason(request))
    if request.readiness not in _EXECUTION_READY_STATES:
        return (False, "Execution-triggering operator action blocked: readiness_not_ready.")
    if request.requested_action is None:
        return (False, "Execution-triggering operator action blocked: missing_requested_action.")
    if request.action_allowed is not True:
        return (False, "Execution-triggering operator action blocked: action_not_allowed.")
    if request.blockers:
        return (False, "Execution-triggering operator action blocked: unresolved_blockers.")
    if request.requested_action in request.blocked_actions:
        return (False, "Execution-triggering operator action blocked: requested_action_blocked.")
    if request.workflow_state not in _EXECUTION_WORKFLOW_STATES:
        return (False, "Execution-triggering operator action blocked: workflow_not_execution_compatible.")
    if request.requires_human_approval and request.approval_state != "approved":
        return (False, "Execution-triggering operator action blocked: approval_required.")
    if (
        not request.requires_human_approval
        and request.approval_state not in _NON_REQUIRED_APPROVAL_STATES
    ):
        return (False, "Execution-triggering operator action blocked: approval_required.")
    return (True, _allowed_reason(request))


_OPERATOR_CLASSES = {"execution_triggering", "state_shaping"}
_READINESS_STATES = {"not_ready", "ready", "execution_ready"}
_EXECUTION_READY_STATES = {"ready", "execution_ready"}
_EXECUTION_WORKFLOW_STATES = {"execution_prep_ready", "handoff_packet_created"}
_NON_REQUIRED_APPROVAL_STATES = {"not_required", "not_requested", "approved"}
