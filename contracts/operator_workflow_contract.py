from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.operator_state_contract import OperatorStateAction


OperatorWorkflowState = Literal[
    "new_request_received",
    "input_blocked",
    "clarification_required",
    "clarification_in_progress",
    "plan_generated",
    "plan_review_required",
    "plan_ready_only",
    "execution_blocked",
    "human_approval_required",
    "execution_prep_ready",
    "handoff_packet_created",
    "post_plan_follow_up",
    "scope_reset",
]
OperatorWorkflowTransition = Literal[
    "request_received",
    "input_hard_stop",
    "clarification_required",
    "clarification_in_progress",
    "plan_generated",
    "plan_review_required",
    "plan_ready_only",
    "execution_blocked",
    "human_approval_required",
    "execution_prep_ready",
    "handoff_packet_created",
    "post_plan_follow_up",
    "scope_reset",
]
ApprovalState = Literal["not_requested", "pending", "approved", "rejected"]


class OperatorHandoffPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    trace_id: str | None = None
    brief: dict[str, Any] | None = None
    readiness: dict[str, Any] | None = None
    blockers: list[str] = Field(default_factory=list)
    approval_state: ApprovalState


class OperatorWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: str | None = None
    errors: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    brief: dict[str, Any] | None = None
    clarification_needed: bool | None = None
    missing_fields: list[str] = Field(default_factory=list)
    clarification_active: bool = False
    execution_readiness: dict[str, Any] | None = None
    operator_action: OperatorStateAction | None = None
    approval_state: ApprovalState = "not_requested"
    create_handoff_packet: bool = False


class OperatorWorkflowResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    state: OperatorWorkflowState
    transition: OperatorWorkflowTransition
    allowed_operator_actions: list[str] = Field(default_factory=list)
    blocked_operator_actions: list[str] = Field(default_factory=list)
    requires_human_approval: bool
    execution_prep_eligible: bool
    recovery_action: str | None = None
    audit_tags: list[str] = Field(default_factory=list)
    handoff_packet: OperatorHandoffPacket | None = None


def map_operator_workflow(
    request: OperatorWorkflowInput,
) -> OperatorWorkflowResult:
    if request.operator_action and (
        request.operator_action.reset_required
        or request.operator_action.action in {"reset_scope", "shift_goal"}
    ):
        return _result(
            state="scope_reset",
            transition="scope_reset",
            audit_tags=["operator_scope_reset"],
        )

    if request.clarification_active:
        return _result(
            state="clarification_in_progress",
            transition="clarification_in_progress",
            allowed=["supply_field", "replace_field", "request_options", "reset_scope"],
            recovery_action="supply_requested_field",
            audit_tags=["clarification_active"],
        )

    if request.clarification_needed or request.missing_fields:
        return _result(
            state="clarification_required",
            transition="clarification_required",
            allowed=["supply_field", "request_options", "reset_scope"],
            recovery_action="request_missing_fields",
            audit_tags=["clarification_required"],
        )

    readiness = request.execution_readiness or {}
    readiness_level = readiness.get("readiness_level")
    requested_action = readiness.get("requested_action")
    action_allowed = readiness.get("action_allowed")
    allowed_actions = list(readiness.get("allowed_actions") or [])
    blocked_actions = list(readiness.get("blocked_actions") or [])
    blockers = list(readiness.get("blocking_reasons") or [])

    if requested_action and action_allowed is False:
        return _result(
            state="execution_blocked",
            transition="execution_blocked",
            allowed=allowed_actions,
            blocked=blocked_actions,
            recovery_action="resolve_execution_blockers",
            audit_tags=["execution_blocked", readiness_level] if readiness_level else ["execution_blocked"],
        )

    if request.status and request.status != "pass":
        return _result(
            state="input_blocked",
            transition="input_hard_stop",
            blocked=["plan_display", "calendar_review", "calendar_schedule", "booking_prep"],
            recovery_action="revise_request",
            audit_tags=["input_blocked"],
        )

    if readiness_level == "plan_ready_only":
        return _result(
            state="plan_ready_only",
            transition="plan_ready_only",
            allowed=allowed_actions,
            blocked=blocked_actions,
            recovery_action="review_plan_or_refine_details",
            audit_tags=["plan_ready_only"],
        )

    if readiness_level == "execution_ready":
        if request.create_handoff_packet and request.approval_state == "approved":
            return _result(
                state="handoff_packet_created",
                transition="handoff_packet_created",
                allowed=allowed_actions,
                blocked=blocked_actions,
                execution_prep_eligible=True,
                audit_tags=["execution_ready", "handoff_packet_created"],
                handoff_packet=_handoff_packet(request, blockers),
            )
        if request.approval_state == "approved":
            return _result(
                state="execution_prep_ready",
                transition="execution_prep_ready",
                allowed=allowed_actions,
                blocked=blocked_actions,
                execution_prep_eligible=True,
                audit_tags=["execution_ready", "human_approved"],
            )
        return _result(
            state="human_approval_required",
            transition="human_approval_required",
            allowed=["plan_display", "calendar_review"],
            blocked=["calendar_schedule", "booking_prep"],
            requires_human_approval=True,
            recovery_action="collect_human_approval",
            audit_tags=["execution_ready", "approval_required"],
        )

    if request.status == "pass":
        return _result(
            state="plan_review_required",
            transition="plan_review_required",
            allowed=["plan_display"],
            recovery_action="operator_review_plan",
            audit_tags=["plan_generated", "review_required"],
        )

    return _result(
        state="new_request_received",
        transition="request_received",
        recovery_action="route_request",
        audit_tags=["new_request_received"],
    )


def _result(
    *,
    state: OperatorWorkflowState,
    transition: OperatorWorkflowTransition,
    allowed: list[str] | None = None,
    blocked: list[str] | None = None,
    requires_human_approval: bool = False,
    execution_prep_eligible: bool = False,
    recovery_action: str | None = None,
    audit_tags: list[str] | None = None,
    handoff_packet: OperatorHandoffPacket | None = None,
) -> OperatorWorkflowResult:
    return OperatorWorkflowResult(
        state=state,
        transition=transition,
        allowed_operator_actions=allowed or [],
        blocked_operator_actions=blocked or [],
        requires_human_approval=requires_human_approval,
        execution_prep_eligible=execution_prep_eligible,
        recovery_action=recovery_action,
        audit_tags=audit_tags or [],
        handoff_packet=handoff_packet,
    )


def _handoff_packet(
    request: OperatorWorkflowInput,
    blockers: list[str],
) -> OperatorHandoffPacket:
    return OperatorHandoffPacket(
        trace_id=request.trace_id,
        brief=request.brief,
        readiness=request.execution_readiness,
        blockers=blockers,
        approval_state=request.approval_state,
    )
