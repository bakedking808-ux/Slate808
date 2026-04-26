import pytest
from engine.clarification_runner import run, reset_state

def setup_function():
    reset_state()

def test_active_timing_clarification_accepts_valid_range():
    reset_state()
    run("Plan a trip to Nakuru")
    out = run("4th-8th May")
    assert "how many travellers" in out.lower()
    assert "exact dates" not in out.lower()  # Should not repeat vague prompt

def test_active_timing_clarification_handles_month_first():
    reset_state()
    run("Plan a trip to Nakuru")
    out = run("Aug 23-30")
    assert "how many travellers" in out.lower() and "exact dates" not in out.lower()

def test_active_budget_clarification_accepts_budget_80k():
    reset_state()
    run("Plan a trip to Nakuru")
    run("4th-8th May")
    out = run("Budget 80k")
    assert "80000" in out or "budget" in out.lower()
    assert "specify your budget" not in out.lower()

def test_malformed_budget_80000k_correction():
    reset_state()
    run("Plan a trip to Nakuru")
    run("4th-8th May")
    out = run("80000K")
    assert "please enter the budget" in out.lower() or "correction" in out.lower()
    assert "80000k" not in out.lower()

def test_approval_continuation():
    reset_state()
    run("Plan a trip to Nakuru")
    run("4th-8th May")
    run("Budget 80k")
    run("Group trip")
    out = run("Approved")
    assert "approval" in out.lower() or "approved" in out.lower() or "handoff" in out.lower()

def test_approval_like_input_outside_approval_state():
    reset_state()
    out = run("Approved")
    assert "travel planning only" in out.lower() or "not supported" in out.lower() or "reject" in out.lower() or "fail" in out.lower()

def test_active_mood_clarification_accepts_quiet_retreat():
    reset_state()
    run("Plan a trip to Nakuru")
    run("4th-8th May")
    run("Budget 80k")
    out = run("Quiet retreat")
    assert "quiet retreat" in out.lower() or "mood" in out.lower()
    assert "what kind of trip mood" not in out.lower()
