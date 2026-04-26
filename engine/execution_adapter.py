from __future__ import annotations

import hashlib
import json
from typing import Any

from contracts.execution_adapter_contract import (
    ExecutionAdapterRequest,
    ExecutionAdapterResult,
)


REVIEW_ONLY_WORKFLOW_STATES = {
    "plan_ready_only",
    "human_approval_required",
    "execution_prep_ready",
    "handoff_packet_created",
}
PREP_ONLY_WORKFLOW_STATES = {
    "plan_ready_only",
    "human_approval_required",
    "execution_prep_ready",
    "handoff_packet_created",
}
MUTATION_PREVIEW_WORKFLOW_STATES = {
    "execution_prep_ready",
    "handoff_packet_created",
}
PLAN_READY_LEVELS = {"plan_ready_only", "execution_ready"}


def run_execution_adapter_dry_run(
    request: ExecutionAdapterRequest,
) -> ExecutionAdapterResult:
    payload_hash = _payload_hash(request.payload)
    failure_class, message, recovery = _precondition_failure(request)
    if failure_class is not None:
        return _result(
            request=request,
            status="failure",
            payload_hash=payload_hash,
            failure_class=failure_class,
            message=message,
            recovery_guidance=recovery,
        )

    return _result(
        request=request,
        status="success",
        payload_hash=payload_hash,
        message="Dry-run adapter request validated; no external mutation attempted.",
    )


def _precondition_failure(
    request: ExecutionAdapterRequest,
) -> tuple[str | None, str, str | None]:
    if not request.requested_action:
        return ("input_incomplete", "requested_action is required.", "Provide an explicit requested action.")
    if request.dry_run is not True:
        return ("policy_blocked", "Only dry-run adapter execution is supported.", "Set dry_run to true.")
    if not request.idempotency_key:
        return ("precondition_failed", "idempotency_key is required.", "Provide a deterministic idempotency key.")
    if not request.readiness_level:
        return ("input_incomplete", "readiness_level is required.", "Provide readiness truth before adapter entry.")
    if request.blockers:
        return ("precondition_failed", "Adapter entry blocked by unresolved blockers.", "Resolve blockers before adapter entry.")
    if _missing_execution_inputs(request):
        return ("input_incomplete", "Adapter request is missing explicit execution inputs.", "Provide target, resource, and payload fields.")

    if request.action_class == "review_only":
        return _review_only_failure(request)
    if request.action_class == "prep_only":
        return _prep_only_failure(request)
    return _mutation_capable_failure(request)


def _review_only_failure(
    request: ExecutionAdapterRequest,
) -> tuple[str | None, str, str | None]:
    if request.readiness_level not in PLAN_READY_LEVELS:
        return ("precondition_failed", "review_only adapters require plan-ready or execution-ready readiness.", "Return to planning readiness.")
    if request.workflow_state not in REVIEW_ONLY_WORKFLOW_STATES:
        return ("precondition_failed", "workflow_state is not compatible with review_only adapter entry.", "Return to an allowed workflow state.")
    return (None, "", None)


def _prep_only_failure(
    request: ExecutionAdapterRequest,
) -> tuple[str | None, str, str | None]:
    if request.readiness_level not in PLAN_READY_LEVELS:
        return ("precondition_failed", "prep_only adapters require at least plan-ready readiness.", "Return to plan-ready workflow.")
    if request.workflow_state not in PREP_ONLY_WORKFLOW_STATES:
        return ("precondition_failed", "workflow_state is not compatible with prep_only adapter entry.", "Return to an allowed workflow state.")
    return (None, "", None)


def _mutation_capable_failure(
    request: ExecutionAdapterRequest,
) -> tuple[str | None, str, str | None]:
    if request.readiness_level != "execution_ready":
        return ("precondition_failed", "mutation_capable dry-run previews require execution-ready readiness.", "Resolve execution readiness first.")
    if request.workflow_state not in MUTATION_PREVIEW_WORKFLOW_STATES:
        return ("precondition_failed", "workflow_state is not compatible with mutation preview.", "Collect approval before mutation preview.")
    if request.approval_state != "approved":
        return ("approval_missing", "mutation_capable dry-run previews require approved state.", "Collect explicit human approval.")
    return (None, "", None)


def _missing_execution_inputs(request: ExecutionAdapterRequest) -> bool:
    return not (
        request.target_parameters
        and request.resource_identifiers
        and request.payload
        and request.mapping_schema_version
        and request.goal
        and request.travel_brief
    )


def _result(
    *,
    request: ExecutionAdapterRequest,
    status: str,
    payload_hash: str,
    message: str,
    failure_class: str | None = None,
    recovery_guidance: str | None = None,
) -> ExecutionAdapterResult:
    return ExecutionAdapterResult(
        status=status,
        dry_run=request.dry_run,
        action_class=request.action_class,
        requested_action=request.requested_action,
        mutation_attempted=False,
        mutation_performed=False,
        failure_class=failure_class,
        message=message,
        recovery_guidance=recovery_guidance,
        payload_hash=payload_hash,
        request_summary=_request_summary(request),
        created_at=request.created_at,
        completed_at=request.created_at,
    )


def _request_summary(request: ExecutionAdapterRequest) -> dict[str, Any]:
    return {
        "trace_id": request.trace_id,
        "adapter_name": request.adapter_name,
        "adapter_version": request.adapter_version,
        "workflow_state": request.workflow_state,
        "readiness_level": request.readiness_level,
        "approval_state": request.approval_state,
        "mapping_schema_version": request.mapping_schema_version,
    }


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
