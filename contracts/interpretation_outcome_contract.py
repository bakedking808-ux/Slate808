from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any

class InterpretationOutcome(Enum):
    INTERPRET = auto()
    CLARIFY = auto()
    CORRECT = auto()
    REJECT = auto()

class InterpretationTargetField(Enum):
    DESTINATION = "destination"
    TIMING = "timing"
    TRAVELLER_COUNT = "traveller_count"
    BUDGET = "budget"
    MOOD = "mood"
    APPROVAL = "approval"
    RESET = "reset"
    UNKNOWN = "unknown"

class InterpretationReasonCode(Enum):
    VALID_FIELD_ANSWER = "valid_field_answer"
    MISSING_PRECISION = "missing_precision"
    MISSING_MONTH = "missing_month"
    MALFORMED_MONTH = "malformed_month"
    AMBIGUOUS_DESTINATION = "ambiguous_destination"
    AMBIGUOUS_TRAVELLER_COUNT = "ambiguous_traveller_count"
    MALFORMED_BUDGET = "malformed_budget"
    BUDGET_RANGE_REQUIRES_CLARIFICATION = "budget_range_requires_clarification"
    APPROVAL_EXPECTED = "approval_expected"
    APPROVAL_NOT_EXPECTED = "approval_not_expected"
    OUT_OF_SCOPE = "out_of_scope"
    UNSUPPORTED_CONTEXT_REFERENCE = "unsupported_context_reference"
    UNSAFE_OR_UNUSABLE = "unsafe_or_unusable"
    NO_ACTIVE_CLARIFICATION = "no_active_clarification"

@dataclass(frozen=True)
class InterpretationResult:
    outcome: InterpretationOutcome
    target_field: InterpretationTargetField
    extracted_value: Optional[Any] = None
    clarification_prompt: Optional[str] = None
    correction_prompt: Optional[str] = None
    reason_code: Optional[InterpretationReasonCode] = None
    confidence_level: Optional[str] = None  # e.g., "high", "medium", "low"
    should_advance_workflow: bool = False
    should_repeat_prompt: bool = False
    state_update_allowed: bool = False

@dataclass(frozen=True)
class InterpretationContext:
    active_field: Optional[InterpretationTargetField] = None
    workflow_state: Optional[str] = None
    clarification_attempt_count: int = 0
    previous_prompt: Optional[str] = None
    has_active_clarification: bool = False
    approval_expected: bool = False

# Helper constructors
def interpret_result(target_field, extracted_value, reason_code=None, confidence_level=None):
    return InterpretationResult(
        outcome=InterpretationOutcome.INTERPRET,
        target_field=target_field,
        extracted_value=extracted_value,
        reason_code=reason_code or InterpretationReasonCode.VALID_FIELD_ANSWER,
        confidence_level=confidence_level or "high",
        should_advance_workflow=True,
        should_repeat_prompt=False,
        state_update_allowed=True
    )

def clarify_result(target_field, clarification_prompt, reason_code, confidence_level=None):
    return InterpretationResult(
        outcome=InterpretationOutcome.CLARIFY,
        target_field=target_field,
        clarification_prompt=clarification_prompt,
        reason_code=reason_code,
        confidence_level=confidence_level or "medium",
        should_advance_workflow=False,
        should_repeat_prompt=False,
        state_update_allowed=False
    )

def correct_result(target_field, correction_prompt, reason_code, confidence_level=None):
    return InterpretationResult(
        outcome=InterpretationOutcome.CORRECT,
        target_field=target_field,
        correction_prompt=correction_prompt,
        reason_code=reason_code,
        confidence_level=confidence_level or "medium",
        should_advance_workflow=False,
        should_repeat_prompt=False,
        state_update_allowed=False
    )

def reject_result(target_field, reason_code, confidence_level=None):
    return InterpretationResult(
        outcome=InterpretationOutcome.REJECT,
        target_field=target_field,
        reason_code=reason_code,
        confidence_level=confidence_level or "low",
        should_advance_workflow=False,
        should_repeat_prompt=False,
        state_update_allowed=False
    )
