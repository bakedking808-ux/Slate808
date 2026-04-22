from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.operator_flow_contract import OperatorFlowResult


OperatorActionType = Literal[
    "none",
    "replace_field",
    "supply_field",
    "request_options",
    "resume_previous",
    "reset_scope",
    "shift_goal",
    "complete_flow",
]


class OperatorStateAction(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    action: OperatorActionType
    target_field: str | None
    reset_required: bool
    resume_allowed: bool
    reason: str


class OperatorStateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    matched: bool
    action: OperatorStateAction | None = None
    warnings: list[str] = Field(default_factory=list)


def interpret_operator_state(
    signal_result: OperatorFlowResult,
) -> OperatorStateResult:
    if not signal_result.matched or signal_result.signal is None:
        return OperatorStateResult(matched=False, action=None, warnings=[])

    signal = signal_result.signal
    text = signal.normalized_text.lower()
    target_field = _target_field(text)

    if signal.signal_type == "intent_declaration":
        return _matched(
            action="none",
            target_field=None,
            reset_required=False,
            resume_allowed=False,
            reason="Fresh intent declaration does not require operator-state handling.",
        )

    if signal.signal_type == "information_correction":
        return _matched(
            action="replace_field",
            target_field=target_field,
            reset_required=False,
            resume_allowed=True,
            reason="Operator input indicates a correction to previously supplied information.",
        )

    if signal.signal_type == "information_supply":
        return _matched(
            action="supply_field",
            target_field=target_field,
            reset_required=False,
            resume_allowed=True,
            reason="Operator input supplies missing or requested information.",
        )

    if signal.signal_type == "clarification_request":
        return _matched(
            action="request_options",
            target_field=None,
            reset_required=False,
            resume_allowed=True,
            reason="Operator input requests clarification or options.",
        )

    if signal.signal_type == "meta_instruction":
        return _interpret_meta_instruction(text, target_field)

    if signal.signal_type == "goal_shift":
        return _matched(
            action="shift_goal",
            target_field=None,
            reset_required=True,
            resume_allowed=False,
            reason="Operator input changes the direction or type of trip planning.",
        )

    if signal.signal_type == "completion_signal":
        return _matched(
            action="complete_flow",
            target_field=None,
            reset_required=False,
            resume_allowed=False,
            reason="Operator input signals acceptance or completion.",
        )

    return OperatorStateResult(matched=False, action=None, warnings=[])


def _matched(
    action: OperatorActionType,
    target_field: str | None,
    reset_required: bool,
    resume_allowed: bool,
    reason: str,
    warnings: list[str] | None = None,
) -> OperatorStateResult:
    return OperatorStateResult(
        matched=True,
        action=OperatorStateAction(
            action=action,
            target_field=target_field,
            reset_required=reset_required,
            resume_allowed=resume_allowed,
            reason=reason,
        ),
        warnings=warnings or [],
    )


def _interpret_meta_instruction(
    text: str,
    target_field: str | None,
) -> OperatorStateResult:
    if re.search(r"\bcontinue\s+from\s+where\s+we\s+left\s+off\b", text):
        return _matched(
            action="resume_previous",
            target_field=None,
            reset_required=False,
            resume_allowed=True,
            reason="Operator input requests resuming the previous flow.",
        )

    if re.search(r"\b(?:start\s+over|restart)\b", text):
        return _matched(
            action="reset_scope",
            target_field=None,
            reset_required=True,
            resume_allowed=False,
            reason="Operator input requests resetting the current scope.",
        )

    return _matched(
        action="none",
        target_field=target_field,
        reset_required=False,
        resume_allowed=False,
        reason="Meta instruction is recognized but not actionable in v1.",
        warnings=["Meta instruction recognized but not actionable in v1."],
    )


def _target_field(text: str) -> str | None:
    if re.search(r"\b(?:people|person|travellers|travelers|two people|\d+\s+people)\b", text):
        return "traveller_count"

    if re.search(r"\bdestination\b", text):
        return "destination"

    if re.search(r"\bbudget\b", text):
        return "budget"

    if re.search(r"\b(?:date|dates|next month|next week|weekend)\b", text):
        return "timing"

    return None
