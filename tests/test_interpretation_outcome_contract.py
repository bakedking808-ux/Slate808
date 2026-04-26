import pytest
from contracts.interpretation_outcome_contract import (
    InterpretationOutcome,
    InterpretationTargetField,
    InterpretationReasonCode,
    InterpretationResult,
    InterpretationContext,
    interpret_result,
    clarify_result,
    correct_result,
    reject_result
)

def test_interpret_result_timing():
    result = interpret_result(
        target_field=InterpretationTargetField.TIMING,
        extracted_value="4th may to 8th may"
    )
    assert result.outcome == InterpretationOutcome.INTERPRET
    assert result.target_field == InterpretationTargetField.TIMING
    assert result.extracted_value == "4th may to 8th may"
    assert result.should_advance_workflow is True
    assert result.should_repeat_prompt is False
    assert result.state_update_allowed is True

def test_clarify_result_destination():
    result = clarify_result(
        target_field=InterpretationTargetField.DESTINATION,
        clarification_prompt="Please specify which destination you mean.",
        reason_code=InterpretationReasonCode.AMBIGUOUS_DESTINATION
    )
    assert result.outcome == InterpretationOutcome.CLARIFY
    assert result.target_field == InterpretationTargetField.DESTINATION
    assert result.clarification_prompt is not None
    assert result.reason_code == InterpretationReasonCode.AMBIGUOUS_DESTINATION
    assert result.should_advance_workflow is False

def test_correct_result_timing():
    result = correct_result(
        target_field=InterpretationTargetField.TIMING,
        correction_prompt="Did you mean August?",
        reason_code=InterpretationReasonCode.MALFORMED_MONTH
    )
    assert result.outcome == InterpretationOutcome.CORRECT
    assert result.target_field == InterpretationTargetField.TIMING
    assert result.correction_prompt is not None
    assert result.reason_code == InterpretationReasonCode.MALFORMED_MONTH
    assert result.should_repeat_prompt is False

def test_reject_result_approval():
    result = reject_result(
        target_field=InterpretationTargetField.APPROVAL,
        reason_code=InterpretationReasonCode.APPROVAL_NOT_EXPECTED
    )
    assert result.outcome == InterpretationOutcome.REJECT
    assert result.target_field == InterpretationTargetField.APPROVAL
    assert result.reason_code == InterpretationReasonCode.APPROVAL_NOT_EXPECTED
    assert result.state_update_allowed is False

def test_interpretation_context_active_clarification():
    context = InterpretationContext(
        active_field=InterpretationTargetField.TIMING,
        workflow_state="clarification_in_progress",
        clarification_attempt_count=1,
        has_active_clarification=True
    )
    assert context.active_field == InterpretationTargetField.TIMING
    assert context.workflow_state == "clarification_in_progress"
    assert context.clarification_attempt_count == 1
    assert context.has_active_clarification is True

def test_reason_codes_are_deterministic():
    # Ensure all reason codes are from the enum, not freeform
    for code in InterpretationReasonCode:
        assert isinstance(code.value, str)
    # Ensure outcomes are not freeform
    for outcome in InterpretationOutcome:
        assert outcome.name in {"INTERPRET", "CLARIFY", "CORRECT", "REJECT"}
