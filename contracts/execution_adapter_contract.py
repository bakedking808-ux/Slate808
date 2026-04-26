from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AdapterActionClass = Literal["review_only", "prep_only", "mutation_capable"]
AdapterStatus = Literal["success", "failure"]
AdapterFailureClass = Literal[
    "input_incomplete",
    "precondition_failed",
    "approval_missing",
    "approval_expired",
    "policy_blocked",
    "auth_unavailable",
    "connectivity_failure",
    "timeout",
    "rate_limited",
    "external_validation_failed",
    "external_rejected",
    "idempotency_conflict",
    "unknown_adapter_failure",
]


class ExecutionAdapterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    trace_id: str
    adapter_name: str
    adapter_version: str
    action_class: AdapterActionClass
    requested_action: str | None
    dry_run: bool
    idempotency_key: str | None
    workflow_state: str
    readiness_level: str | None
    approval_state: str
    goal: str
    travel_brief: dict[str, Any]
    blockers: list[str] = Field(default_factory=list)
    target_parameters: dict[str, Any]
    resource_identifiers: dict[str, Any]
    payload: dict[str, Any]
    mapping_schema_version: str
    created_at: str


class ExecutionAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: AdapterStatus
    dry_run: bool
    action_class: AdapterActionClass
    requested_action: str | None
    mutation_attempted: bool
    mutation_performed: bool
    failure_class: AdapterFailureClass | None = None
    message: str
    recovery_guidance: str | None = None
    payload_hash: str
    request_summary: dict[str, Any]
    created_at: str
    completed_at: str
