import pytest
from contracts.interpretation_outcome_contract import *
from engine.interpretation import *

def make_context(**kwargs):
    return InterpretationContext(**kwargs)

def test_timing_ambiguity():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("4-8", ctx)
    assert r.outcome == InterpretationOutcome.CORRECT
    assert r.reason_code == InterpretationReasonCode.MISSING_MONTH
    assert "month" in r.correction_prompt.lower()

def test_timing_valid_range():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("4th-8th May", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.TIMING
    assert r.extracted_value == "4th-8th May"

def test_timing_valid_range_august():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("23-30 August", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.TIMING
    assert r.extracted_value == "23-30 August"

def test_timing_month_first():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("August 23-30", ctx)
    assert r.outcome in [InterpretationOutcome.INTERPRET, InterpretationOutcome.CORRECT]
    if r.outcome == InterpretationOutcome.CORRECT:
        assert r.reason_code == InterpretationReasonCode.MALFORMED_MONTH
    else:
        assert r.extracted_value == "August 23-30"

def test_timing_relative():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("next weekend", ctx)
    assert r.outcome == InterpretationOutcome.CLARIFY
    assert r.reason_code == InterpretationReasonCode.MISSING_PRECISION

def test_timing_tomorrow():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("tomorrow 10AM-5PM", ctx)
    assert r.outcome == InterpretationOutcome.CLARIFY
    assert r.reason_code == InterpretationReasonCode.MISSING_PRECISION

def test_month_typo_augurts():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("23-24 Augurts", ctx)
    assert r.outcome == InterpretationOutcome.CORRECT
    assert r.reason_code == InterpretationReasonCode.MALFORMED_MONTH
    assert "august" in r.correction_prompt.lower()

def test_month_typo_agust():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("4th-6th Agust", ctx)
    assert r.outcome == InterpretationOutcome.CORRECT
    assert r.reason_code == InterpretationReasonCode.MALFORMED_MONTH
    assert "august" in r.correction_prompt.lower()

def test_month_typo_februry():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("12-14 Februry", ctx)
    assert r.outcome == InterpretationOutcome.CORRECT
    assert r.reason_code == InterpretationReasonCode.MALFORMED_MONTH
    assert "february" in r.correction_prompt.lower()

def test_budget_80k():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("80k", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.BUDGET
    assert r.extracted_value == 80000

def test_budget_80000():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("80,000", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.BUDGET
    assert r.extracted_value == 80000

def test_budget_80000k():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("80000K", ctx)
    assert r.outcome == InterpretationOutcome.CORRECT
    assert r.reason_code == InterpretationReasonCode.MALFORMED_BUDGET

def test_budget_friendly():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("budget friendly", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.extracted_value == "budget_friendly"

def test_budget_range():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("budget is 30-40k", ctx)
    assert r.outcome == InterpretationOutcome.CLARIFY
    assert r.reason_code == InterpretationReasonCode.BUDGET_RANGE_REQUIRES_CLARIFICATION

def test_budget_vague():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("cheap but clean", ctx)
    assert r.outcome == InterpretationOutcome.CLARIFY
    assert r.reason_code == InterpretationReasonCode.MISSING_PRECISION

def test_approval_true():
    ctx = make_context(active_field=InterpretationTargetField.APPROVAL, approval_expected=True)
    r = interpret_input("Approved", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.APPROVAL
    assert r.extracted_value is True

def test_approval_false():
    ctx = make_context(active_field=InterpretationTargetField.APPROVAL, approval_expected=True)
    r = interpret_input("Declined", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.APPROVAL
    assert r.extracted_value is False

def test_approval_reject():
    ctx = make_context(active_field=InterpretationTargetField.APPROVAL, approval_expected=False)
    r = interpret_input("Approved", ctx)
    assert r.outcome == InterpretationOutcome.REJECT
    assert r.reason_code == InterpretationReasonCode.APPROVAL_NOT_EXPECTED

def test_resume_destination():
    ctx = make_context(active_field=InterpretationTargetField.DESTINATION, has_active_clarification=True)
    r = interpret_input("Nakuru", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.DESTINATION
    assert r.extracted_value == "nakuru"

def test_resume_traveller_count():
    ctx = make_context(active_field=InterpretationTargetField.TRAVELLER_COUNT, has_active_clarification=True)
    r = interpret_input("6 adults", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.TRAVELLER_COUNT
    assert r.extracted_value == 6

def test_resume_budget():
    ctx = make_context(active_field=InterpretationTargetField.BUDGET, has_active_clarification=True)
    r = interpret_input("Budget 80k", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.BUDGET
    assert r.extracted_value == 80000

def test_resume_mood():
    ctx = make_context(active_field=InterpretationTargetField.MOOD, has_active_clarification=True)
    r = interpret_input("Quiet retreat", ctx)
    assert r.outcome in [InterpretationOutcome.INTERPRET, InterpretationOutcome.CLARIFY]
    if r.outcome == InterpretationOutcome.INTERPRET:
        assert r.extracted_value == "quiet retreat"

def test_resume_timing():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r = interpret_input("23-30 August", ctx)
    assert r.outcome == InterpretationOutcome.INTERPRET
    assert r.target_field == InterpretationTargetField.TIMING
    assert r.extracted_value == "23-30 August"

def test_determinism():
    ctx = make_context(active_field=InterpretationTargetField.TIMING, has_active_clarification=True)
    r1 = interpret_input("4th-8th May", ctx)
    r2 = interpret_input("4th-8th May", ctx)
    assert r1 == r2
