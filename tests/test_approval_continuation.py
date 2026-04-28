from engine.clarification_runner import run, reset_state


def test_approved_outside_approval_state_is_not_travel_request():
    reset_state()

    out = run("Approved")

    assert "Slate808 currently supports travel planning only" in out
    assert "Travel Brief:" not in out


def test_exact_date_trip_reaches_human_approval_required():
    reset_state()

    out = run("Plan a relaxed trip to Naivasha for 2 people 4th May to 8th May")

    assert "Slate808 Output" in out
    assert "Status: pass" in out
    assert "- Destination: Naivasha" in out
    assert "- Traveller Count: 2" in out
    assert "- Timing: 4th May to 8th May" in out
    assert "- Trip Mood: Relaxed" in out
    assert "- State: human_approval_required" in out
    assert "- Human Approval Required: True" in out
    assert "- Execution Prep Eligible: False" in out


def test_approved_after_human_approval_required_moves_to_execution_prep_ready():
    reset_state()

    first = run("Plan a relaxed trip to Naivasha for 2 people 4th May to 8th May")
    assert "- State: human_approval_required" in first

    out = run("Approved")

    assert "Slate808 currently supports travel planning only" not in out
    assert "- State: execution_prep_ready" in out
    assert "- Approval State: approved" in out
    assert "- Execution Prep Eligible: True" in out


def test_declined_after_human_approval_required_blocks_execution_prep():
    reset_state()

    first = run("Plan a relaxed trip to Naivasha for 2 people 4th May to 8th May")
    assert "- State: human_approval_required" in first

    out = run("Declined")

    assert "Slate808 currently supports travel planning only" not in out
    assert "- State: plan_ready_only" in out
    assert "- Approval State: rejected" in out
    assert "Execution-prep remains blocked" in out
